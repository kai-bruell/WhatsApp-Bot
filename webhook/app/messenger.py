"""
Messenger-Modul: Sendet Nachrichten ueber die Meta WhatsApp Cloud API.
"""

import httpx

from app.config import META_API_URL, WHATSAPP_TOKEN

HEADERS = {
    "Authorization": f"Bearer {WHATSAPP_TOKEN}",
    "Content-Type": "application/json",
}


async def _post(payload: dict) -> int:
    """Sendet einen POST-Request an die Meta API und gibt den Statuscode zurueck."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(META_API_URL, headers=HEADERS, json=payload)
        print(f"[MESSENGER] API {resp.status_code}: {resp.text}")
        return resp.status_code


async def send_text(to: str, body: str) -> None:
    """Sendet eine einfache Textnachricht."""
    print(f"[MESSENGER] send_text -> {to}: {body[:80]}")
    await _post({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    })


async def send_interactive_buttons(to: str, body_text: str, buttons: list[dict]) -> None:
    """Sendet eine Nachricht mit Quick-Reply-Buttons."""
    print(f"[MESSENGER] send_interactive_buttons -> {to}")
    await _post({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body_text},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
                    for b in buttons
                ]
            },
        },
    })


async def send_list_message(to: str, body_text: str, button_text: str, sections: list[dict]) -> None:
    """Sendet eine List Message (Auswahl-Menu)."""
    print(f"[MESSENGER] send_list_message -> {to}")
    await _post({
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body_text},
            "action": {
                "button": button_text,
                "sections": sections,
            },
        },
    })
