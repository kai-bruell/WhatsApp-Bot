"""Shared SQLite connection for all stores."""

import sqlite3

from app.config import RATE_LIMIT_DB

_conn: sqlite3.Connection | None = None


def get_db() -> sqlite3.Connection:
    """Returns a shared SQLite connection (created on first call)."""
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(RATE_LIMIT_DB, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
    return _conn
