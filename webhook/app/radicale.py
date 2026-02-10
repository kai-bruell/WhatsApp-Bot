"""
Radicale-Modul: Synchronisiert Kontakte mit dem Radicale CardDAV-Server.

Aktuell nur Platzhalter - die eigentlichen HTTP-Calls zu Radicale
werden spaeter implementiert.
"""

from app.config import RADICALE_URL, RADICALE_USER, RADICALE_PASSWORD, RADICALE_ADDRESSBOOK


async def sync_contact(phone_number: str, display_name: str) -> None:
    """
    Laedt eine vCard via HTTP PUT auf den Radicale-Server.

    Spaeter: Generiert die vCard, sendet PUT-Request an
    {RADICALE_URL}/{RADICALE_USER}/{RADICALE_ADDRESSBOOK}/{phone_number}.vcf
    """
    target_url = f"{RADICALE_URL}/{RADICALE_USER}/{RADICALE_ADDRESSBOOK}/{phone_number}.vcf"

    print(f"[RADICALE] sync_contact aufgerufen: {display_name} ({phone_number})")
    print(f"[RADICALE] Ziel-URL: {target_url}")
    print(f"[RADICALE] Hier wuerde ein HTTP PUT mit der vCard an Radicale gesendet.")
    print(f"[RADICALE] Auth: {RADICALE_USER} / ****")

    # TODO: Echten Sync aktivieren
    # vcard_content = await create_vcard(phone_number, display_name)
    # async with httpx.AsyncClient() as client:
    #     resp = await client.put(
    #         target_url,
    #         content=vcard_content,
    #         auth=(RADICALE_USER, RADICALE_PASSWORD),
    #         headers={"Content-Type": "text/vcard"},
    #     )
    #     print(f"[RADICALE] Response: {resp.status_code}")


async def delete_contact(phone_number: str) -> None:
    """
    Loescht eine vCard vom Radicale-Server via HTTP DELETE.
    """
    target_url = f"{RADICALE_URL}/{RADICALE_USER}/{RADICALE_ADDRESSBOOK}/{phone_number}.vcf"

    print(f"[RADICALE] delete_contact aufgerufen: {phone_number}")
    print(f"[RADICALE] Ziel-URL: {target_url}")
    print(f"[RADICALE] Hier wuerde ein HTTP DELETE an Radicale gesendet.")

    # TODO: Echten Delete aktivieren


async def get_contact(phone_number: str) -> dict | None:
    """
    Liest eine vCard vom Radicale-Server via HTTP GET.
    """
    target_url = f"{RADICALE_URL}/{RADICALE_USER}/{RADICALE_ADDRESSBOOK}/{phone_number}.vcf"

    print(f"[RADICALE] get_contact aufgerufen: {phone_number}")
    print(f"[RADICALE] Ziel-URL: {target_url}")
    print(f"[RADICALE] Hier wuerde ein HTTP GET an Radicale gesendet.")

    # TODO: Echten GET aktivieren und vCard parsen
    return None
