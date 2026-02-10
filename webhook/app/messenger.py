"""
Messenger-Modul: Sendet Nachrichten ueber die Meta WhatsApp Cloud API.

Alle Funktionen sind Platzhalter, die den jeweiligen API-Call beschreiben,
aber noch keinen echten HTTP-Request ausfuehren.
"""

import httpx

from app.config import META_API_URL, WHATSAPP_TOKEN


async def send_text(to: str, body: str) -> None:
    """Sendet eine einfache Textnachricht an eine WhatsApp-Nummer."""
    print(f"[MESSENGER] send_text -> An: {to}")
    print(f"[MESSENGER] Inhalt: {body}")

    # TODO: Echten API-Call aktivieren
    # headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    # payload = {
    #     "messaging_product": "whatsapp",
    #     "to": to,
    #     "type": "text",
    #     "text": {"body": body},
    # }
    # async with httpx.AsyncClient() as client:
    #     resp = await client.post(META_API_URL, headers=headers, json=payload)
    #     print(f"[MESSENGER] API-Response: {resp.status_code}")


async def send_interactive_buttons(to: str, body_text: str, buttons: list[dict]) -> None:
    """
    Sendet eine Nachricht mit Quick-Reply-Buttons.

    buttons: [{"id": "btn_id", "title": "Button Text"}, ...]
    """
    print(f"[MESSENGER] send_interactive_buttons -> An: {to}")
    print(f"[MESSENGER] Body: {body_text}")
    print(f"[MESSENGER] Buttons: {buttons}")

    # TODO: Echten API-Call aktivieren
    # headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    # payload = {
    #     "messaging_product": "whatsapp",
    #     "recipient_type": "individual",
    #     "to": to,
    #     "type": "interactive",
    #     "interactive": {
    #         "type": "button",
    #         "body": {"text": body_text},
    #         "action": {
    #             "buttons": [
    #                 {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
    #                 for b in buttons
    #             ]
    #         },
    #     },
    # }
    # async with httpx.AsyncClient() as client:
    #     resp = await client.post(META_API_URL, headers=headers, json=payload)
    #     print(f"[MESSENGER] API-Response: {resp.status_code}")


async def send_list_message(to: str, body_text: str, button_text: str, sections: list[dict]) -> None:
    """
    Sendet eine List Message (Auswahl-Menu).

    sections: [{"title": "Abschnitt", "rows": [{"id": "row_1", "title": "Option"}]}]
    """
    print(f"[MESSENGER] send_list_message -> An: {to}")
    print(f"[MESSENGER] Body: {body_text}, Button: {button_text}")
    print(f"[MESSENGER] Sections: {sections}")

    # TODO: Echten API-Call aktivieren
