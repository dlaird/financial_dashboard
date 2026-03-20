"""
email_poller.py — Gmail IMAP poller for the email-to-YNAB pipeline.

Run on a schedule (Windows Task Scheduler) to pick up new "ynab" emails,
parse them, and write pending transactions to pending_transactions.db.

Usage:
    python email_poller.py

Email format (Phase 1 — structured):
    Subject: ynab          (case-insensitive, just needs to contain "ynab")
    Body:
        amount: 47.23
        account: chase
        payee: Whole Foods
        category: groceries
        memo: weekly shopping    (optional)
        date: 2026-03-18         (optional — defaults to today)
"""

import imaplib
import email
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


def _get_body(msg) -> str:
    """Extract plain-text body from an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            disp = str(part.get("Content-Disposition", ""))
            if ct == "text/plain" and "attachment" not in disp:
                charset = part.get_content_charset() or "utf-8"
                return part.get_payload(decode=True).decode(charset, errors="replace")
    else:
        charset = msg.get_content_charset() or "utf-8"
        return msg.get_payload(decode=True).decode(charset, errors="replace")
    return ""


def fetch_ynab_emails() -> list[dict]:
    """
    Connect to Gmail via IMAP, fetch unread emails whose subject contains
    SUBJECT_TRIGGER, mark them as read, and return raw email dicts.
    """
    gmail_user = os.getenv("GMAIL_ADDRESS")
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD")
    if not gmail_user or not gmail_pass:
        raise ValueError("GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be set in .env")

    results = []
    with imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT) as imap:
        imap.login(gmail_user, gmail_pass)
        imap.select("INBOX")

        # Search for unread emails with "ynab" in the subject (case-insensitive)
        _, msg_ids = imap.search(None, f'(UNSEEN SUBJECT "{SUBJECT_TRIGGER}")')
        ids = msg_ids[0].split()
        log.info(f"Found {len(ids)} unread YNAB email(s).")

        for msg_id in ids:
            _, data = imap.fetch(msg_id, "(RFC822)")
            raw = data[0][1]
            msg = email.message_from_bytes(raw)

            subject = _decode_header_value(msg.get("Subject", ""))
            body = _get_body(msg)
            received = msg.get("Date", "")

            results.append({
                "raw_subject": subject,
                "raw_body": body,
                "received_at": received,
                "msg_id": msg_id,
            })

            # Mark as read
            imap.store(msg_id, "+FLAGS", "\\Seen")

    return results


# ---------------------------------------------------------------------------
# Phase 1 parser — positional body (no keywords needed)
# ---------------------------------------------------------------------------

def _parse_positional(body: str) -> dict[str, str]:
    """
    Parse a positional email body.  Lines are read top-to-bottom; blank lines ignored.

    Position 0: amount   (e.g. 47.23  or  $47.23)
    Position 1: account  (shortcut or full name)
    Position 2: payee
    Position 3: category (shortcut or full name)
    Position 4+: memo    (all remaining lines joined as one string, optional)
    """
    lines = [l.strip() for l in body.splitlines() if l.strip()]
    result = {}
    if len(lines) > 0: result["amount"]   = lines[0]
    if len(lines) > 1: result["account"]  = lines[1]
    if len(lines) > 2: result["payee"]    = lines[2]
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


def _parse_date(raw: str | None) -> str:
    """Return ISO date string; defaults to today."""
    if not raw:
        return date_cls.today().isoformat()
    # Accept MM/DD/YYYY, M/D/YY, YYYY-MM-DD
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return date_cls.fromisoformat(raw) if fmt == "%Y-%m-%d" else \
                   __import__("datetime").datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return date_cls.today().isoformat()


def parse_phase1(raw_subject: str, raw_body: str, received_at: str) -> dict:
    """
    Parse a positional YNAB email into a pending_transaction record.
    Line order: amount / account / payee / category / memo (optional)
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
    tx_date = _parse_date(kv.get("date"))

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

def run():
    log.info("Email poller starting.")
    try:
        emails = fetch_ynab_emails()
    except Exception as e:
        log.error(f"Failed to fetch emails: {e}")
        return

    inserted = 0
    for em in emails:
        try:
            record = parse_phase1(em["raw_subject"], em["raw_body"], em["received_at"])
            tx_id = pending_db.insert_pending(record)
            log.info(
                f"Inserted pending tx #{tx_id}: "
                f"{record.get('payee')} ${abs((record.get('amount_milliunits') or 0) / 1000):.2f}"
                + (f" [warnings: {record['parse_warnings']}]" if record.get("parse_warnings") else "")
            )
            inserted += 1
        except Exception as e:
            log.error(f"Failed to process email '{em['raw_subject']}': {e}")

    log.info(f"Done. {inserted} transaction(s) queued.")


if __name__ == "__main__":
    run()
