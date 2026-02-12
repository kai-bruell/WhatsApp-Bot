"""
Rate Limiter — SQLite-persistenter Zaehler fuer SMS, Email, API und Callbacks.

Prueft Rolling-Window-Limits pro Sender und global.
Alle Schwellwerte werden aus config.py (Environment) gelesen.
"""

import time

from app.db import get_db
from app.config import (
    RATE_SMS_PER_USER_DAY,
    RATE_SMS_GLOBAL_DAY,
    RATE_EMAIL_PER_USER_DAY,
    RATE_EMAIL_GLOBAL_DAY,
    RATE_API_GLOBAL_HOUR,
    RATE_API_PER_USER_HOUR,
)

_DAY = 86_400
_HOUR = 3_600


class RateLimiter:
    def __init__(self) -> None:
        self._conn = get_db()
        self._init_db()
        self._cleanup()

    def _init_db(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS rate_events (
                bucket TEXT NOT NULL,
                timestamp REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_rate_bucket_ts
                ON rate_events(bucket, timestamp);
            CREATE TABLE IF NOT EXISTS callbacks (
                sender TEXT PRIMARY KEY,
                requested_at REAL NOT NULL
            );
        """)
        self._conn.commit()

    def _cleanup(self) -> None:
        """Entfernt abgelaufene Eintraege (aelter als 1 Tag)."""
        cutoff = time.time() - _DAY
        self._conn.execute("DELETE FROM rate_events WHERE timestamp <= ?", (cutoff,))
        self._conn.commit()

    # -- interne Helfer --

    def _count(self, bucket: str, window: int) -> int:
        cutoff = time.time() - window
        row = self._conn.execute(
            "SELECT COUNT(*) FROM rate_events WHERE bucket = ? AND timestamp > ?",
            (bucket, cutoff),
        ).fetchone()
        return row[0]

    def _remaining_seconds(self, bucket: str, window: int) -> int:
        """Berechnet, wann der aelteste Eintrag im Fenster ablaeuft."""
        cutoff = time.time() - window
        row = self._conn.execute(
            "SELECT MIN(timestamp) FROM rate_events WHERE bucket = ? AND timestamp > ?",
            (bucket, cutoff),
        ).fetchone()
        if not row or row[0] is None:
            return 0
        remaining = (row[0] + window) - time.time()
        return max(1, int(remaining) + 1)

    def _record(self, *buckets: str) -> None:
        now = time.time()
        self._conn.executemany(
            "INSERT INTO rate_events (bucket, timestamp) VALUES (?, ?)",
            [(b, now) for b in buckets],
        )
        self._conn.commit()

    # -- SMS --

    def check_sms(self, sender: str) -> tuple[str, int] | None:
        """Gibt (i18n-Key, Wartezeit in Sek.) zurueck, falls Limit erreicht."""
        user_bucket = f"sms:user:{sender}"
        if self._count(user_bucket, _DAY) >= RATE_SMS_PER_USER_DAY:
            return ("rate_limit_sms_user", self._remaining_seconds(user_bucket, _DAY))
        if self._count("sms:global", _DAY) >= RATE_SMS_GLOBAL_DAY:
            return ("rate_limit_sms_global", self._remaining_seconds("sms:global", _DAY))
        return None

    def record_sms(self, sender: str) -> None:
        self._record(f"sms:user:{sender}", "sms:global")

    # -- Email --

    def check_email(self, sender: str) -> tuple[str, int] | None:
        """Gibt (i18n-Key, Wartezeit in Sek.) zurueck, falls Limit erreicht."""
        user_bucket = f"email:user:{sender}"
        if self._count(user_bucket, _DAY) >= RATE_EMAIL_PER_USER_DAY:
            return ("rate_limit_email_user", self._remaining_seconds(user_bucket, _DAY))
        if self._count("email:global", _DAY) >= RATE_EMAIL_GLOBAL_DAY:
            return ("rate_limit_email_global", self._remaining_seconds("email:global", _DAY))
        return None

    def record_email(self, sender: str) -> None:
        self._record(f"email:user:{sender}", "email:global")

    # -- API (eingehende Nachrichten) --

    def check_api(self, sender: str) -> tuple[str, int] | None:
        """Gibt (i18n-Key, Wartezeit in Sek.) zurueck, falls Limit erreicht."""
        user_bucket = f"api:user:{sender}"
        if self._count(user_bucket, _HOUR) >= RATE_API_PER_USER_HOUR:
            return ("rate_limit_api_user", self._remaining_seconds(user_bucket, _HOUR))
        if self._count("api:global", _HOUR) >= RATE_API_GLOBAL_HOUR:
            return ("rate_limit_api_global", self._remaining_seconds("api:global", _HOUR))
        return None

    def record_api(self, sender: str) -> None:
        self._record(f"api:user:{sender}", "api:global")

    # -- Callbacks --

    def callback_count(self, sender: str) -> int:
        """Gibt die Anzahl der Rueckruf-Anforderungen im 24h-Fenster zurueck."""
        return self._count(f"callback:user:{sender}", _DAY)

    def record_callback(self, sender: str) -> None:
        """Speichert eine Rueckruf-Anforderung."""
        self._record(f"callback:user:{sender}")

    # -- Datenloeschung --

    def purge_user(self, phone: str) -> None:
        """Loescht alle Rate-Limit- und Callback-Daten eines Nutzers."""
        self._conn.execute(
            "DELETE FROM rate_events WHERE bucket LIKE ?", (f"%{phone}%",),
        )
        self._conn.execute("DELETE FROM callbacks WHERE sender = ?", (phone,))
        self._conn.commit()
        print(f"[RATE LIMIT] purge_user({phone})")


limiter = RateLimiter()
