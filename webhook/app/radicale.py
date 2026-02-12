"""
Radicale-Modul: Synchronisiert Kontakte mit dem Radicale CardDAV-Server.
"""

from app.config import RADICALE_URL, RADICALE_USER, RADICALE_ADDRESSBOOK


async def sync_contact(phone_number: str, display_name: str) -> None:
    """Platzhalter: HTTP PUT an Radicale."""
    print(f"[RADICALE] STUB sync_contact({phone_number}, {display_name})")


async def delete_contact(phone_number: str) -> None:
    """Platzhalter: HTTP DELETE an Radicale."""
    print(f"[RADICALE] STUB delete_contact({phone_number})")
