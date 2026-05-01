"""
email_poller.py — Gmail IMAP poller for the email-to-YNAB pipeline.

Run on a schedule (Windows Task Scheduler) to pick up new "ynab" emails,
parse them, and write pending transactions to pending_transactions.db.

Usage:
    .venv/bin/python email_poller.py

Email format (Phase 1 — structured):
    Subject: ynab          (case-insensitive, just needs to contain "ynab")
    Body:
        47.23              (amount — required)
        Whole Foods        (payee  — required)
        chase              (account shortcut — required)
        groceries          (category shortcut — required)
        weekly shopping    (memo — optional)

    Transaction date defaults to the email's sent date.
"""

import imaplib
import email
import email.utils
import json
import os
import re
import logging
from datetime import date as date_cls
from email.header import decode_header
from dotenv import load_dotenv

import pending_db
import ynab_writer as yw

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler("email_poller.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
SUBJECT_TRIGGER = "ynab"   # case-insensitive; subject just needs to contain this

_SOURCES_PATH = os.path.join(os.path.dirname(__file__), "phase2_sources.json")

def _load_sources() -> dict:
    with open(_SOURCES_PATH) as f:
        return json.load(f)


def _match_sender_rule(original_from: str, rules: list[dict]) -> dict | None:
    """Return the first rule whose domain, address, or name_contains matches original_from."""
    addr = original_from.lower()
    for rule in rules:
        if "address" in rule and rule["address"].lower() in addr:
            return rule
        if "domain" in rule and rule["domain"].lower() in addr:
            return rule
        if "name_contains" in rule and rule["name_contains"].lower() in addr:
            return rule
    return None


def _extract_forwarded_from(body: str) -> str:
    """
    Extract the original (deepest) sender from a forwarded message chain.

    Handles double-forwards (e.g. vet → wife → you): scans for ALL
    'Forwarded message' blocks and returns the From line of the last one,
    which is the furthest-upstream original sender.
    """
    matches = re.findall(
        r"[-]{5,}\s*Forwarded message\s*[-]{5,}.*?From:\s*(.+?)(?=\n\S|\Z)",
        body,
        re.IGNORECASE | re.DOTALL,
    )
    if matches:
        return " ".join(matches[-1].split())
    return ""


# ---------------------------------------------------------------------------
# IMAP helpers
# ---------------------------------------------------------------------------

def _decode_header_value(raw) -> str:
    parts = decode_header(raw)
    decoded = []
    for part, enc in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return "".join(decoded)


def _html_to_lines(html: str) -> str:
    """Convert an HTML body to newline-separated plain text.
    Replaces <br> and block-level tags with newlines, then strips all tags."""
    import re
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</(p|div|li|tr|h[1-6])>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    import html as html_module
    return html_module.unescape(text)


def _get_body(msg) -> str:
    """Extract plain-text body from an email message.

    Prefers text/plain; falls back to parsing text/html when Gmail (and other
    clients) collapse multiple lines into a single space-separated line in the
    plain-text part.
    """
    plain, html_body = None, None

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if "attachment" in disp:
                continue
            raw = part.get_payload(decode=True)
            if raw is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            payload = raw.decode(charset, errors="replace")
            if ct == "text/plain" and plain is None:
                plain = payload
            elif ct == "text/html" and html_body is None:
                html_body = payload
    else:
        charset = msg.get_content_charset() or "utf-8"
        plain = msg.get_payload(decode=True).decode(charset, errors="replace")

    # Use plain text if it contains more than one non-empty line; otherwise
    # fall back to the HTML part (Gmail often collapses lines in text/plain).
    if plain:
        non_empty = [l for l in plain.splitlines() if l.strip()]
        if len(non_empty) > 1:
            return plain

    if html_body:
        return _html_to_lines(html_body)

    return plain or ""


def fetch_ynab_emails() -> list[dict]:
    """
    Connect to Gmail via IMAP and fetch all unread emails from trusted forwarders.
    Emails are NOT marked as read here — call mark_emails_read() after processing.
    """
    gmail_user = os.getenv("GMAIL_ADDRESS")
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD")
    if not gmail_user or not gmail_pass:
        raise ValueError("GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be set in .env")

    sources = _load_sources()
    trusted = {addr.lower() for addr in sources.get("trusted_forwarders", {}).keys()}

    results = []
    with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) as imap:
        imap.login(gmail_user, gmail_pass)
        imap.select("INBOX")

        since = (date_cls.today().replace(day=1) - __import__("datetime").timedelta(days=1)).replace(day=1)
        since_str = since.strftime("%d-%b-%Y")  # IMAP format: 01-Mar-2026
        _, msg_ids = imap.search(None, f"(UNSEEN SINCE {since_str})")
        ids = msg_ids[0].split()
        log.info(f"Found {len(ids)} unread email(s) since {since_str}.")

        for msg_id in ids:
            _, data = imap.fetch(msg_id, "(BODY.PEEK[])")
            raw = data[0][1]
            msg = email.message_from_bytes(raw)

            from_raw = _decode_header_value(msg.get("From", ""))
            from_addr = re.search(r"[\w.\-+]+@[\w.\-]+", from_raw)
            from_addr = from_addr.group(0).lower() if from_addr else ""

            if from_addr not in trusted:
                log.info(f"Skipping email from untrusted sender: {from_addr!r}")
                continue

            subject = _decode_header_value(msg.get("Subject", ""))
            body = _get_body(msg)
            received = msg.get("Date", "")

            results.append({
                "raw_subject": subject,
                "raw_body": body,
                "received_at": received,
                "from_addr": from_addr,
                "msg_id": msg_id,
            })

    log.info(f"Processing {len(results)} email(s) from trusted forwarders.")
    return results


def mark_emails_read(msg_ids: list) -> None:
    """Mark a list of IMAP message IDs as read (\\Seen)."""
    if not msg_ids:
        return
    gmail_user = os.getenv("GMAIL_ADDRESS")
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD")
    with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) as imap:
        imap.login(gmail_user, gmail_pass)
        imap.select("INBOX")
        for msg_id in msg_ids:
            imap.store(msg_id, "+FLAGS", "\\Seen")


# ---------------------------------------------------------------------------
# Phase 1 parser — positional body (no keywords needed)
# ---------------------------------------------------------------------------

def _parse_positional(body: str) -> dict[str, str]:
    """
    Parse a positional email body.  Lines are read top-to-bottom; blank lines ignored.

    Position 0: amount   (e.g. 47.23  or  $47.23)
    Position 1: payee
    Position 2: account  (shortcut or full name)
    Position 3: category (shortcut or full name)
    Position 4+: memo    (all remaining lines joined as one string, optional)
    """
    lines = [l.strip() for l in body.splitlines() if l.strip()]
    result = {}
    if len(lines) > 0: result["amount"]   = lines[0]
    if len(lines) > 1: result["payee"]    = lines[1]
    if len(lines) > 2: result["account"]  = lines[2]
    if len(lines) > 3: result["category"] = lines[3]
    if len(lines) > 4: result["memo"]     = " ".join(lines[4:])
    return result


def _parse_amount(raw: str) -> tuple[int | None, str | None]:
    """
    Parse a dollar amount string like '$47.23' or '47.23' into milliunits.
    YNAB expenses are negative milliunits.
    Returns (milliunits, warning).
    """
    cleaned = re.sub(r"[^\d.]", "", raw)
    try:
        dollars = float(cleaned)
        milliunits = -int(round(dollars * 1000))   # negative = expense
        return milliunits, None
    except ValueError:
        return None, f"Could not parse amount: '{raw}'"


def _parse_email_date(received_at: str) -> str:
    """Parse an RFC 2822 email Date header into an ISO date string."""
    try:
        return email.utils.parsedate_to_datetime(received_at).date().isoformat()
    except Exception:
        return date_cls.today().isoformat()


def _parse_date(raw: str | None, default: str) -> str:
    """Return ISO date string; falls back to default (normally the email's sent date)."""
    if not raw:
        return default
    # Accept MM/DD/YYYY, M/D/YY, YYYY-MM-DD
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return date_cls.fromisoformat(raw) if fmt == "%Y-%m-%d" else \
                   __import__("datetime").datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return default


def parse_phase1(raw_subject: str, raw_body: str, received_at: str) -> dict:
    """
    Parse a positional YNAB email into a pending_transaction record.
    Line order: amount / payee / account / category / memo (optional)
    Transaction date defaults to the email's sent date.
    """
    kv = _parse_positional(raw_body)
    warnings = []

    # --- amount ---
    amount_milliunits, warn = _parse_amount(kv.get("amount", ""))
    if warn:
        warnings.append(warn)

    # --- account ---
    acct_id, acct_name, warn = yw.resolve_account(kv.get("account"))
    if warn:
        warnings.append(warn)

    # --- payee ---
    payee = kv.get("payee", "").strip()
    if not payee:
        warnings.append("No payee specified.")

    # --- category ---
    cat_raw = kv.get("category", "").strip()
    cat_id, cat_name, warn = yw.resolve_category(cat_raw) if cat_raw else (None, None, "No category specified.")
    if warn:
        warnings.append(warn)

    # --- optional fields ---
    memo = kv.get("memo", "").strip() or None
    email_date = _parse_email_date(received_at)
    tx_date = _parse_date(kv.get("date"), default=email_date)

    return {
        "received_at": received_at,
        "status": "pending",
        "raw_subject": raw_subject,
        "raw_body": raw_body,
        "payee": payee or None,
        "amount_milliunits": amount_milliunits,
        "date": tx_date,
        "account_id": acct_id,
        "account_name": acct_name,
        "category_id": cat_id,
        "category_name": cat_name,
        "memo": memo,
        "parse_warnings": "; ".join(warnings) if warnings else None,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _log_inserted(record: dict, tx_id: int) -> None:
    log.info(
        f"Inserted pending tx #{tx_id}: "
        f"{record.get('payee')} ${abs((record.get('amount_milliunits') or 0) / 1000):.2f}"
        + (f" [warnings: {record['parse_warnings']}]" if record.get("parse_warnings") else "")
    )


def run():
    log.info("Email poller starting.")
    try:
        emails = fetch_ynab_emails()
    except Exception as e:
        log.error(f"Failed to fetch emails: {e}")
        return

    sources = _load_sources()
    trusted_forwarders = sources.get("trusted_forwarders", {})  # {addr: prefix}
    sender_rules = sources.get("sender_rules", [])

    inserted = 0
    read_ids = []   # msg_ids to mark read — only on successful insert

    for em in emails:
        subject = em["raw_subject"]
        body = em["raw_body"]
        received = em["received_at"]
        from_addr = em["from_addr"]
        msg_id = em["msg_id"]

        try:
            if SUBJECT_TRIGGER in subject.lower():
                # ── Phase 1: structured manual email ──────────────────────────
                record = parse_phase1(subject, body, received)
                tx_id = pending_db.insert_pending(record)
                _log_inserted(record, tx_id)
                inserted += 1
                read_ids.append(msg_id)

            else:
                # ── Phase 2: forwarded bill / receipt ─────────────────────────
                import phase2_parser as p2

                forwarded_from = _extract_forwarded_from(body)
                rule = _match_sender_rule(forwarded_from, sender_rules)
                if not rule:
                    log.info(
                        f"No sender rule for forwarded-from '{forwarded_from}' — "
                        f"leaving unread."
                    )
                    continue

                forwarder_prefix = trusted_forwarders.get(from_addr, "?")
                payee_hint = rule.get("payee", "")

                log.info(f"Phase 2: extracting from '{payee_hint}' email forwarded by {from_addr}.")
                extracted = p2.extract_transactions(body, payee_hint=payee_hint)
                if not extracted:
                    log.warning(f"Claude returned no transactions for subject: '{subject}' — leaving unread.")
                    continue

                records = p2.build_pending_records(
                    extracted=extracted,
                    rule=rule,
                    forwarder_prefix=forwarder_prefix,
                    raw_subject=subject,
                    raw_body=body,
                    received_at=received,
                )
                for record in records:
                    tx_id = pending_db.insert_pending(record)
                    _log_inserted(record, tx_id)
                    inserted += 1
                if records:
                    read_ids.append(msg_id)

        except Exception as e:
            log.error(f"Failed to process email '{subject}': {e}", exc_info=True)

    mark_emails_read(read_ids)
    log.info(f"Done. {inserted} transaction(s) queued.")


if __name__ == "__main__":
    run()
