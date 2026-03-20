"""
pending_db.py — SQLite helpers for the email-to-YNAB pending transaction queue.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "pending_transactions.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pending_transactions (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                received_at         TEXT    NOT NULL,
                status              TEXT    NOT NULL DEFAULT 'pending',
                raw_subject         TEXT,
                raw_body            TEXT,
                payee               TEXT,
                amount_milliunits   INTEGER,
                date                TEXT,
                account_id          TEXT,
                account_name        TEXT,
                category_id         TEXT,
                category_name       TEXT,
                memo                TEXT,
                parse_warnings      TEXT,
                ynab_transaction_id TEXT
            )
        """)
        conn.commit()


def insert_pending(record: dict) -> int:
    """Insert a new pending transaction. Returns the new row id."""
    cols = [
        "received_at", "status", "raw_subject", "raw_body",
        "payee", "amount_milliunits", "date",
        "account_id", "account_name",
        "category_id", "category_name",
        "memo", "parse_warnings",
    ]
    placeholders = ", ".join("?" for _ in cols)
    col_str = ", ".join(cols)
    values = [record.get(c) for c in cols]
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO pending_transactions ({col_str}) VALUES ({placeholders})",
            values,
        )
        conn.commit()
        return cur.lastrowid


def get_pending() -> list[dict]:
    """Return all transactions with status='pending', newest first."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM pending_transactions WHERE status = 'pending' ORDER BY received_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def update_transaction(tx_id: int, updates: dict):
    """Update arbitrary fields on a transaction by id."""
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [tx_id]
    with get_conn() as conn:
        conn.execute(
            f"UPDATE pending_transactions SET {set_clause} WHERE id = ?",
            values,
        )
        conn.commit()


def approve_transaction(tx_id: int, ynab_transaction_id: str):
    update_transaction(tx_id, {"status": "approved", "ynab_transaction_id": ynab_transaction_id})


def reject_transaction(tx_id: int):
    update_transaction(tx_id, {"status": "rejected"})


# Initialise the DB on import so it always exists before anything tries to use it.
init_db()
