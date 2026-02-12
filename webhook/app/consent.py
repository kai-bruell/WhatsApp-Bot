"""
Consent-Store — Verwaltet DSGVO-Einwilligungen in einer SQLite-Tabelle.
"""

from datetime import datetime, timezone

from app.db import get_db


class ConsentStore:
    """SQLite-Store fuer Consent-Records (teilt DB mit RateLimiter)."""

    def __init__(self) -> None:
        self._conn = get_db()
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS consents (
                phone       TEXT PRIMARY KEY,
                consented   INTEGER NOT NULL,
                updated_at  TEXT NOT NULL
            )
        """)
        self._conn.commit()

    def has_record(self, phone: str) -> bool:
        """Wurde der User schon gefragt?"""
        row = self._conn.execute(
            "SELECT 1 FROM consents WHERE phone = ?", (phone,)
        ).fetchone()
        return row is not None

    def has_consented(self, phone: str) -> bool:
        """Hat der User zugestimmt?"""
        row = self._conn.execute(
            "SELECT consented FROM consents WHERE phone = ?", (phone,)
        ).fetchone()
        return bool(row and row[0])

    def store_consent(self, phone: str, consented: bool) -> None:
        """Speichert oder aktualisiert die Einwilligung (UPSERT)."""
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "INSERT INTO consents (phone, consented, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(phone) DO UPDATE SET consented = excluded.consented, "
            "updated_at = excluded.updated_at",
            (phone, int(consented), now),
        )
        self._conn.commit()
        print(f"[CONSENT] store_consent({phone}, {consented})")

    def revoke_consent(self, phone: str) -> None:
        """Setzt consented=0."""
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "UPDATE consents SET consented = 0, updated_at = ? WHERE phone = ?",
            (now, phone),
        )
        self._conn.commit()
        print(f"[CONSENT] revoke_consent({phone})")

    def delete_record(self, phone: str) -> None:
        """Loescht den Eintrag komplett (fuer Re-Consent nach Datenloeschung)."""
        self._conn.execute("DELETE FROM consents WHERE phone = ?", (phone,))
        self._conn.commit()
        print(f"[CONSENT] delete_record({phone})")


consent_store = ConsentStore()
