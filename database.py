"""
database.py
Persistent storage for MarketMind Academy (paper trading). SQLite via the
Python standard library — no server to run, one file (academy.db) that
lives next to app.py and survives restarts.

This is deliberately a separate database from the main app's watchlist.json
/ portfolio.json, per the Academy branch being isolated from the main
research app. Nothing here is imported by the main branch's code paths.

Scaling note: SQLite is genuinely fine for a single-server app with a
modest number of concurrent users. If Academy grows into a real hosted
multi-user product, the natural next step is Postgres — the function
signatures below (each takes/returns plain dicts) are written so that
swap wouldn't require touching any calling code, just this file's guts.
"""

from __future__ import annotations
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = Path(__file__).parent / "academy.db"

STARTING_CASH = 5000.00


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Creates all tables if they don't exist yet. Safe to call every run."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                cash_balance REAL NOT NULL DEFAULT 5000.00,
                disclaimer_accepted INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                ticker TEXT NOT NULL,
                shares REAL NOT NULL,
                avg_price REAL NOT NULL,
                UNIQUE(user_id, ticker)
            );

            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                ticker TEXT NOT NULL,
                action TEXT NOT NULL,
                shares REAL NOT NULL,
                price REAL NOT NULL,
                realized_pl REAL,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS academy_watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                ticker TEXT NOT NULL,
                UNIQUE(user_id, ticker)
            );

            CREATE TABLE IF NOT EXISTS portfolio_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                total_value REAL NOT NULL,
                recorded_at TEXT NOT NULL
            );
        """)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ----------------------------------------------------------------------
# Users
# ----------------------------------------------------------------------

def create_user(username: str, email: str, password_hash: str) -> dict | None:
    """Returns the new user row, or None if username/email already taken."""
    try:
        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, email, password_hash, cash_balance, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (username, email, password_hash, STARTING_CASH, _now()),
            )
            user_id = cur.lastrowid
        return get_user_by_id(user_id)
    except sqlite3.IntegrityError:
        return None


def get_user_by_username(username: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None


def get_user_by_email(email: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None


def get_user_by_id(user_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def update_password(user_id: int, new_password_hash: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_password_hash, user_id))


def accept_disclaimer(user_id: int) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE users SET disclaimer_accepted = 1 WHERE id = ?", (user_id,))


def update_cash_balance(user_id: int, new_balance: float) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE users SET cash_balance = ? WHERE id = ?", (new_balance, user_id))


# ----------------------------------------------------------------------
# Holdings
# ----------------------------------------------------------------------

def get_holdings(user_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM holdings WHERE user_id = ?", (user_id,)).fetchall()
        return [dict(r) for r in rows]


def get_holding(user_id: int, ticker: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM holdings WHERE user_id = ? AND ticker = ?", (user_id, ticker)
        ).fetchone()
        return dict(row) if row else None


def upsert_holding(user_id: int, ticker: str, shares: float, avg_price: float) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO holdings (user_id, ticker, shares, avg_price)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, ticker) DO UPDATE SET shares = ?, avg_price = ?
        """, (user_id, ticker, shares, avg_price, shares, avg_price))


def delete_holding(user_id: int, ticker: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM holdings WHERE user_id = ? AND ticker = ?", (user_id, ticker))


# ----------------------------------------------------------------------
# Trades
# ----------------------------------------------------------------------

def record_trade(user_id: int, ticker: str, action: str, shares: float, price: float, realized_pl: float | None = None) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO trades (user_id, ticker, action, shares, price, realized_pl, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, ticker, action, shares, price, realized_pl, _now()),
        )


def get_trade_history(user_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM trades WHERE user_id = ? ORDER BY timestamp DESC", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]


# ----------------------------------------------------------------------
# Academy watchlist
# ----------------------------------------------------------------------

def get_academy_watchlist(user_id: int) -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT ticker FROM academy_watchlist WHERE user_id = ?", (user_id,)
        ).fetchall()
        return [r["ticker"] for r in rows]


def add_academy_watchlist(user_id: int, ticker: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO academy_watchlist (user_id, ticker) VALUES (?, ?)",
            (user_id, ticker.upper()),
        )


def remove_academy_watchlist(user_id: int, ticker: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM academy_watchlist WHERE user_id = ? AND ticker = ?",
            (user_id, ticker.upper()),
        )


# ----------------------------------------------------------------------
# Portfolio value history (for a "performance over time" chart later)
# ----------------------------------------------------------------------

def record_portfolio_value(user_id: int, total_value: float) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO portfolio_history (user_id, total_value, recorded_at) VALUES (?, ?, ?)",
            (user_id, total_value, _now()),
        )


def get_portfolio_history(user_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM portfolio_history WHERE user_id = ? ORDER BY recorded_at ASC", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]
