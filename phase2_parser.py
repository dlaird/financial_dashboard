"""
phase2_parser.py — Claude-powered email parser for Phase 2 of the email-to-YNAB pipeline.

Handles real-world HTML emails (Amazon orders, utility bills, etc.) by passing the
email body to Claude and asking it to extract one or more transactions as structured JSON.

Each call returns a list of pending_transaction dicts — one per order/charge detected.
"""

import json
import logging
import os
import re

import anthropic
from dotenv import load_dotenv

import ynab_writer as yw
from email_poller import _parse_amount, _parse_date

load_dotenv()

log = logging.getLogger(__name__)

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY not set in .env")
        _client = anthropic.Anthropic(api_key=key)
    return _client


# ---------------------------------------------------------------------------
# Category list for Claude
# ---------------------------------------------------------------------------

def _category_list() -> str:
    """Return the authoritative YNAB category list for Claude to choose from."""
    cats = yw.get_categories()
    names = sorted(c["name"].strip() for c in cats if not c.get("hidden"))
    return "\n".join(f"  - {n}" for n in names)


# ---------------------------------------------------------------------------
# Claude extraction
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are a financial transaction extractor. You will be given the body of a
forwarded email (Amazon order confirmation, utility bill, grocery receipt, etc.).

Extract every distinct transaction or order. For Amazon emails that contain multiple
separate orders, return one entry per order. For a single charge (utility bill,
grocery total), return one entry.

For each transaction return a JSON object with these fields:
  date        — ISO date string (YYYY-MM-DD). For orders/receipts use the order date.
                For invoices and utility bills use the due date (not the billing period
                start, not the email sent date). If no due date is found, use the
                statement/bill date.
  amount      — positive dollar amount as a number (e.g. 47.23). Total charged, not
                subtotal; include tax and shipping.
  payee       — merchant name (e.g. "Amazon", "Austin Energy").
  category    — pick the single best match from the AVAILABLE CATEGORIES list below.
                For Amazon orders with multiple item types, pick the category of the
                highest-dollar item. Use the exact name from the list.
  memo        — if an order, receipt, invoice, or confirmation number is present,
                start with it (e.g. "Order #123-456: dish soap and paper towels").
                Otherwise one short sentence summarising what was purchased (max 80 chars).
  confidence  — "high", "medium", or "low". Low = amount or date was ambiguous.
  notes       — brief explanation if confidence is not high, else empty string.

Return ONLY a JSON array, no other text. Example:
[
  {{"date": "2026-04-01", "amount": 34.56, "payee": "Amazon", "category": "Groceries",
   "memo": "Dish soap and paper towels", "confidence": "high", "notes": ""}}
]

AVAILABLE CATEGORIES:
{category_list}
"""


def extract_transactions(email_body: str, payee_hint: str = "") -> list[dict]:
    """
    Call Claude to extract transactions from an email body.
    Returns a list of raw dicts straight from Claude (not yet resolved to YNAB IDs).
    """
    system = _SYSTEM_PROMPT.format(category_list=_category_list())
    user_msg = email_body.strip()
    if payee_hint:
        user_msg = f"[This email is from: {payee_hint}]\n\n{user_msg}"

    response = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if Claude wraps the JSON
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        log.error(f"Claude returned invalid JSON: {e}\nRaw response:\n{raw}")
        return []

    # Claude sometimes returns a single object instead of a one-element array
    if isinstance(result, dict):
        result = [result]

    if not isinstance(result, list):
        log.error(f"Claude returned unexpected type {type(result)}: {raw}")
        return []

    log.info(f"Claude extracted {len(result)} transaction(s).")
    for i, item in enumerate(result):
        log.info(f"  [{i}] date={item.get('date')} amount={item.get('amount')} "
                 f"payee={item.get('payee')} category={item.get('category')} "
                 f"confidence={item.get('confidence')}")
    return result


# ---------------------------------------------------------------------------
# Build pending_db records from Claude output
# ---------------------------------------------------------------------------

def build_pending_records(
    extracted: list[dict],
    rule: dict,
    forwarder_prefix: str,
    raw_subject: str,
    raw_body: str,
    received_at: str,
) -> list[dict]:
    """
    Convert Claude's extracted transaction dicts into pending_db record dicts.

    Args:
        extracted:        list of dicts from extract_transactions()
        rule:             the matching sender_rule from phase2_sources.json
        forwarder_prefix: "D" or "M" — prepended to memo
        raw_subject:      original email subject
        raw_body:         full email body (stored for audit)
        received_at:      RFC 2822 Date header of the forwarding email
    """
    from email_poller import _parse_email_date
    email_date = _parse_email_date(received_at)

    records = []
    for item in extracted:
        warnings = []

        # --- amount ---
        raw_amount = str(item.get("amount", ""))
        amount_milliunits, warn = _parse_amount(raw_amount)
        if warn:
            warnings.append(warn)

        # --- date ---
        tx_date = _parse_date(item.get("date"), default=email_date)

        # --- payee ---
        payee = item.get("payee") or rule.get("payee") or ""

        # --- account: from rule, resolved via account shortcuts ---
        account_shortcut = rule.get("account", "")
        acct_id, acct_name, warn = yw.resolve_account(account_shortcut)
        if warn:
            warnings.append(warn)

        # --- payee_rules: override category (and optionally payee) based on extracted name ---
        # Use substring match so "Venmo - Flavian Martinez" hits the "flavian martinez" rule
        payee_rules = rule.get("payee_rules", {})
        payee_lower = payee.lower().strip()
        matched_key = next((k for k in payee_rules if k.lower() in payee_lower), None)
        matched_rule = payee_rules[matched_key] if matched_key else None
        if matched_rule:
            log.info(f"  payee_rule matched '{matched_key}' → overriding category and payee.")
            if "payee" in matched_rule:
                payee = matched_rule["payee"]
            cat_override = matched_rule.get("category", "").strip()
            cat_id, cat_name, warn = yw.resolve_category(cat_override) if cat_override else (None, None, "No category in payee rule.")
            if warn:
                warnings.append(warn)
        else:
            # --- category: Claude's suggestion matched against YNAB ---
            cat_suggestion = (item.get("category") or "").strip()
            cat_id, cat_name, warn = yw.resolve_category(cat_suggestion) if cat_suggestion else (None, None, "No category suggested.")
            if warn:
                warnings.append(warn)

        # --- memo: prefix + Claude's summary ---
        memo_body = (item.get("memo") or "").strip()
        memo = f"{forwarder_prefix}: {memo_body}" if memo_body else forwarder_prefix + ":"

        # --- confidence warning (skip if a payee_rule overrode the category) ---
        if not matched_rule:
            confidence = item.get("confidence", "high")
            if confidence != "high":
                notes = item.get("notes", "")
                warnings.append(f"Claude confidence={confidence}. {notes}".strip())

        records.append({
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
            "memo": memo or None,
            "parse_warnings": "; ".join(warnings) if warnings else None,
        })

    return records
