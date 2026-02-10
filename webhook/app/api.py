from fastapi import APIRouter, Request, Response

from app.config import VERIFY_TOKEN
from app.bot_logic import handle_incoming_message

router = APIRouter()


@router.get("/webhook")
async def verify(request: Request):
    """Webhook-Verifizierung (Handshake mit Meta)."""
    params = request.query_params

    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == VERIFY_TOKEN
    ):
        print("[VERIFY] Webhook erfolgreich verifiziert.")
        return Response(content=params.get("hub.challenge"), media_type="text/plain")

    print("[VERIFY] Fehlgeschlagen - Token stimmt nicht.")
    return Response(content="Forbidden", status_code=403)


@router.post("/webhook")
async def webhook(request: Request):
    """Empfaengt eingehende WhatsApp-Nachrichten und Status-Updates."""
    data = await request.json()

    entries = data.get("entry", [])
    for entry in entries:
        for change in entry.get("changes", []):
            value = change.get("value", {})

            # Status-Updates (sent, delivered, read) ignorieren
            if "statuses" in value:
                print(f"[STATUS] Status-Update erhalten: {value['statuses']}")
                continue

            # Nachrichten verarbeiten
            if "messages" in value:
                contact_info = value.get("contacts", [{}])[0]
                for message in value["messages"]:
                    await handle_incoming_message(message, contact_info)

    return {"status": "ok"}
