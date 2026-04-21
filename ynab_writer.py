"""
ynab_writer.py — YNAB write operations for the email-to-YNAB pipeline.

Responsibilities:
  - Fetch accounts and categories from YNAB (with in-process caching)
  - Resolve category name → category_id
  - Duplicate check before posting
  - POST new transaction to YNAB
"""

import os
import re
import json
import requests
from datetime import datetime, timedelta
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

YNAB_BASE = "https://api.youneedabudget.com/v1"


def _headers():
    token = os.getenv("YNAB_API_TOKEN")
    if not token:
        raise ValueError("YNAB_API_TOKEN not set in .env")
    return {"Authorization": f"Bearer {token}"}


def _budget_id():
    bid = os.getenv("YNAB_BUDGET_ID")
    if not bid:
        raise ValueError("YNAB_BUDGET_ID not set in .env")
    return bid


# ---------------------------------------------------------------------------
# Account helpers
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def get_accounts(include_closed: bool = True) -> list[dict]:
    """Return list of {id, name, closed, deleted} for all accounts."""
    url = f"{YNAB_BASE}/budgets/{_budget_id()}/accounts"
    resp = requests.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    accounts = resp.json()["data"]["accounts"]
    result = [
        {"id": a["id"], "name": a["name"], "closed": a["closed"], "deleted": a.get("deleted", False)}
        for a in accounts
    ]
    if not include_closed:
        result = [a for a in result if not a["closed"]]
    return result


def account_name_to_id(name: str) -> str | None:
    """Case-insensitive lookup of account id by name (searches all accounts including closed)."""
    for acct in get_accounts(include_closed=True):
        if acct["name"].lower() == name.lower():
            return acct["id"]
    return None


# ---------------------------------------------------------------------------
# Category helpers
# ---------------------------------------------------------------------------

@lru_cache(maxsize=None)
def get_categories() -> list[dict]:
    """Return flat list of {id, name, group_name} for all non-hidden categories."""
    url = f"{YNAB_BASE}/budgets/{_budget_id()}/categories"
    resp = requests.get(url, headers=_headers(), timeout=30)
    resp.raise_for_status()
    groups = resp.json()["data"]["category_groups"]
    result = []
    for group in groups:
        for cat in group["categories"]:
            if not cat.get("hidden", False):
                result.append({
                    "id": cat["id"],
                    "name": cat["name"],
                    "group_name": group["name"],
                })
    return result


def category_name_to_id(name: str) -> tuple[str | None, str | None]:
    """
    Look up a category by exact name (case-insensitive).
    Returns (category_id, full_category_name) or (None, None).
    """
    name_lower = name.lower().strip()
    for cat in get_categories():
        if cat["name"].lower().strip() == name_lower:
            return cat["id"], cat["name"]
    return None, None


_BRACKET_RE = re.compile(r"^\[.*?\]\s+'?(.*?)'?\s*$")

def _strip_bracket_format(value: str) -> str:
    """
    Strip the [Group]  'Category Name' wrapper that category_shortcuts.json uses,
    returning just the bare category name that YNAB expects.
    e.g. "[Living Expenses - Household]  'Utilities - Electric'" → "Utilities - Electric"
    """
    m = _BRACKET_RE.match(value.strip())
    return m.group(1).strip() if m else value.strip()


def load_shortcuts() -> dict[str, str]:
    """Load category_shortcuts.json → {shortcut_lower: bare_ynab_category_name}."""
    path = os.path.join(os.path.dirname(__file__), "category_shortcuts.json")
    with open(path, "r") as f:
        raw = json.load(f)
    return {k.lower(): _strip_bracket_format(v) for k, v in raw.items() if not k.startswith("_")}


def load_account_shortcuts() -> dict[str, str]:
    """Load account_shortcuts.json → {shortcut_lower: ynab_account_name}."""
    path = os.path.join(os.path.dirname(__file__), "account_shortcuts.json")
    with open(path, "r") as f:
        raw = json.load(f)
    return {k.lower(): v for k, v in raw.items() if not k.startswith("_")}


def resolve_account(raw_input: str) -> tuple[str | None, str | None, str | None]:
    """
    Resolve a user-supplied account string (shortcut or full name) to
    (account_id, account_name, warning).
    Falls back to DEFAULT_YNAB_ACCOUNT env var if raw_input is None/empty.
    """
    if not raw_input:
        raw_input = os.getenv("DEFAULT_YNAB_ACCOUNT", "")
    if not raw_input:
        return None, None, "No account specified and DEFAULT_YNAB_ACCOUNT not set."

    shortcuts = load_account_shortcuts()
    key = raw_input.lower().strip()
    resolved_name = shortcuts.get(key, raw_input)

    acct_id = account_name_to_id(resolved_name)
    if acct_id:
        return acct_id, resolved_name, None

    warning = f"Account '{raw_input}' not found in YNAB (tried '{resolved_name}'). Edit before approving."
    return None, resolved_name, warning


def resolve_category(raw_input: str) -> tuple[str | None, str | None, str | None]:
    """
    Resolve a user-supplied category string (shortcut or full name) to
    (category_id, category_name, warning).
    Returns warning string if resolution failed, else None.
    """
    shortcuts = load_shortcuts()
    key = raw_input.lower().strip()

    # Try shortcut first, then direct name match
    resolved_name = shortcuts.get(key, raw_input)
    cat_id, cat_name = category_name_to_id(resolved_name)

    if cat_id:
        return cat_id, cat_name, None

    warning = f"Category '{raw_input}' not found in YNAB (tried '{resolved_name}'). Edit before approving."
    return None, resolved_name, warning


# ---------------------------------------------------------------------------
# Duplicate check
# ---------------------------------------------------------------------------

def check_duplicate(date_str: str, amount_milliunits: int, payee: str) -> list[dict]:
    """
    Query YNAB for existing transactions within ±3 days of date with the same
    amount. Returns list of matching transactions (empty = no duplicates found).
    """
    date = datetime.fromisoformat(date_str)
    since = (date - timedelta(days=3)).strftime("%Y-%m-%d")
    url = f"{YNAB_BASE}/budgets/{_budget_id()}/transactions"
    resp = requests.get(url, headers=_headers(), params={"since_date": since}, timeout=30)
    resp.raise_for_status()
    transactions = resp.json()["data"]["transactions"]

    matches = []
    for tx in transactions:
        if tx["amount"] == amount_milliunits:
            tx_date = datetime.fromisoformat(tx["date"])
            if abs((tx_date - date).days) <= 3:
                matches.append({
                    "id": tx["id"],
                    "date": tx["date"],
                    "payee": tx.get("payee_name", ""),
                    "amount_milliunits": tx["amount"],
                    "memo": tx.get("memo", ""),
                })
    return matches


# ---------------------------------------------------------------------------
# Post transaction
# ---------------------------------------------------------------------------

def post_transaction(
    date: str,
    amount_milliunits: int,
    payee: str,
    account_id: str,
    category_id: str | None = None,
    memo: str | None = None,
) -> str:
    """
    POST a transaction to YNAB. Returns the new transaction id.
    amount_milliunits should be negative for expenses (YNAB convention).
    """
    payload = {
        "transaction": {
            "date": date,
            "amount": amount_milliunits,
            "payee_name": payee,
            "account_id": account_id,
            "approved": False,   # land in YNAB as unapproved so you can review there too
            "cleared": "uncleared",
        }
    }
    if category_id:
        payload["transaction"]["category_id"] = category_id
    if memo:
        payload["transaction"]["memo"] = memo

    url = f"{YNAB_BASE}/budgets/{_budget_id()}/transactions"
    resp = requests.post(url, headers=_headers(), json=payload, timeout=30)
    if not resp.ok:
        try:
            detail = resp.json().get("error", {}).get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise requests.HTTPError(
            f"{resp.status_code} {resp.reason} — YNAB: {detail}", response=resp
        )
    return resp.json()["data"]["transaction"]["id"]


# ---------------------------------------------------------------------------
# CLI helpers (run directly to inspect YNAB data)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="YNAB writer utilities")
    parser.add_argument("--list-accounts", action="store_true", help="Print all open YNAB accounts")
    parser.add_argument("--list-categories", action="store_true", help="Print all YNAB categories")
    args = parser.parse_args()

    if args.list_accounts:
        all_accounts = get_accounts(include_closed=True)
        print(f"  {'NAME':<40} {'FLAGS':<15} ID")
        print(f"  {'-'*40} {'-'*15} {'-'*36}")
        for a in all_accounts:
            flags = " ".join(f for f, v in [("[closed]", a["closed"]), ("[deleted]", a["deleted"])] if v)
            print(f"  {a['name']:<40} {flags:<15} {a['id']}")
        print(f"\n  Total: {len(all_accounts)} accounts")

    if args.list_categories:
        for c in get_categories():
            print(f"  [{c['group_name']}]  {c['name']!r}  →  {c['id']}")
