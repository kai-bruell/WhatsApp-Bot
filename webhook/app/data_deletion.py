"""
Data Deletion Callback — Meta verlangt eine Callback-URL, ueber die Nutzer
die Loeschung ihrer Daten anfordern koennen.

Signaturvalidierung, SQLite-Store fuer Loeschanfragen, Datenbereinigung.
"""

import base64
import hashlib
import hmac
import json
import sqlite3
import uuid
from datetime import datetime, timezone

from app.config import APP_SECRET, RATE_LIMIT_DB


class DataDeletionStore:
    """SQLite-Store fuer Data-Deletion-Requests (teilt DB mit RateLimiter)."""

    def __init__(self, db_path: str = RATE_LIMIT_DB) -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS data_deletions (
                confirmation_code TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                requested_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
            )
        """)
        self._conn.commit()

    def create(self, user_id: str) -> str:
        code = uuid.uuid4().hex
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO data_deletions (confirmation_code, user_id, requested_at, status) "
            "VALUES (?, ?, ?, 'pending')",
            (code, user_id, now),
        )
        self._conn.commit()
        return code

    def get_status(self, code: str) -> dict | None:
        row = self._conn.execute(
            "SELECT confirmation_code, user_id, requested_at, status "
            "FROM data_deletions WHERE confirmation_code = ?",
            (code,),
        ).fetchone()
        if not row:
            return None
        return {
            "confirmation_code": row[0],
            "user_id": row[1],
            "requested_at": row[2],
            "status": row[3],
        }

    def mark_completed(self, code: str) -> None:
        self._conn.execute(
            "UPDATE data_deletions SET status = 'completed' WHERE confirmation_code = ?",
            (code,),
        )
        self._conn.commit()


def parse_signed_request(signed_request: str) -> dict | None:
    """Dekodiert und validiert einen Meta signed_request (HMAC-SHA256)."""
    try:
        parts = signed_request.split(".", 1)
        if len(parts) != 2:
            return None

        encoded_sig, encoded_payload = parts

        # Base64url-Decode (Meta nutzt URL-safe Base64 ohne Padding)
        sig = base64.urlsafe_b64decode(encoded_sig + "==")
        payload_bytes = base64.urlsafe_b64decode(encoded_payload + "==")

        expected_sig = hmac.new(
            APP_SECRET.encode(), encoded_payload.encode(), hashlib.sha256
        ).digest()

        if not hmac.compare_digest(sig, expected_sig):
            return None

        return json.loads(payload_bytes)
    except Exception:
        return None


def purge_user_data(user_id: str) -> None:
    """Loescht nutzerbezogene Daten. Aktuell Log-only (kein FB-user_id-Mapping)."""
    print(f"[DATA DELETION] Loeschanfrage fuer Facebook user_id={user_id}")


deletion_store = DataDeletionStore()
