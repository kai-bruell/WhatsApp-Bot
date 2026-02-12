"""
Data Deletion Callback — Meta verlangt eine Callback-URL, ueber die Nutzer
die Loeschung ihrer Daten anfordern koennen.

Signaturvalidierung, SQLite-Store fuer Loeschanfragen, Datenbereinigung.
"""

import base64
import hashlib
import hmac
import json
import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from app.db import get_db
from app.config import APP_SECRET
from app.consent import consent_store
from app.radicale import delete_contact
from app.rate_limit import limiter

# Callback fuer user_state-Cleanup (wird von bot_logic registriert,
# vermeidet Circular-Import).
_state_cleanup: Callable[[str], None] | None = None


def register_state_cleanup(fn: Callable[[str], None]) -> None:
    """Registriert eine Funktion zum Bereinigen des User-State bei Loeschung."""
    global _state_cleanup
    _state_cleanup = fn


class DataDeletionStore:
    """SQLite-Store fuer Data-Deletion-Requests (teilt DB mit RateLimiter)."""

    def __init__(self) -> None:
        self._conn = get_db()
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


async def purge_by_phone(phone: str) -> None:
    """Zentrale Loeschfunktion: entfernt alle personenbezogenen Daten eines Nutzers."""
    print(f"[DATA DELETION] purge_by_phone({phone}) — starte Loeschung")
    consent_store.revoke_consent(phone)
    consent_store.delete_record(phone)
    await delete_contact(phone)
    limiter.purge_user(phone)
    if _state_cleanup:
        _state_cleanup(phone)
    print(f"[DATA DELETION] purge_by_phone({phone}) — abgeschlossen")


async def purge_user_data(user_id: str) -> None:
    """Loescht nutzerbezogene Daten via Meta-Callback (best-effort)."""
    print(f"[DATA DELETION] Loeschanfrage fuer Facebook user_id={user_id}")
    if consent_store.has_record(user_id):
        await purge_by_phone(user_id)
    else:
        print(f"[DATA DELETION] Kein Datensatz fuer user_id={user_id} gefunden (best-effort)")


deletion_store = DataDeletionStore()
