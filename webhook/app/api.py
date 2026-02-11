from pathlib import Path

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse

from app.config import VERIFY_TOKEN
from app.bot_logic import handle_incoming_message
from app.data_deletion import deletion_store, parse_signed_request, purge_user_data

router = APIRouter()

_STATIC_DIR = Path(__file__).parent / "static"


# --- Webhook ---


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


# --- Statische Rechtsseiten ---


@router.get("/privacy")
async def privacy():
    """Datenschutzrichtlinie."""
    html = (_STATIC_DIR / "privacy.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)


@router.get("/terms")
async def terms():
    """Allgemeine Geschaeftsbedingungen."""
    html = (_STATIC_DIR / "terms.html").read_text(encoding="utf-8")
    return HTMLResponse(content=html)


# --- Data Deletion Callback ---


def _status_page_html(title: str, body: str) -> str:
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{title}</title></head>"
        f"<body><h1>{title}</h1>{body}</body></html>"
    )


@router.post("/datadeletion")
async def data_deletion_callback(request: Request):
    """Meta Data Deletion Callback (Server-to-Server)."""
    form = await request.form()
    signed_request = form.get("signed_request", "")

    payload = parse_signed_request(signed_request)
    if payload is None:
        print("[DATA DELETION] Ungueltige Signatur.")
        return Response(content="Invalid signature", status_code=403)

    user_id = str(payload.get("user_id", ""))
    code = deletion_store.create(user_id)
    purge_user_data(user_id)
    deletion_store.mark_completed(code)

    status_url = str(request.url_for("data_deletion_status")) + f"?id={code}"
    print(f"[DATA DELETION] Loeschung abgeschlossen: code={code}, user_id={user_id}")

    return {"url": status_url, "confirmation_code": code}


@router.get("/datadeletion")
async def data_deletion_status(request: Request):
    """HTML-Statusseite fuer eine Data-Deletion-Anfrage."""
    code = request.query_params.get("id", "")

    if not code:
        html = _status_page_html(
            "Data Deletion",
            "<p>Bitte geben Sie eine Confirmation-ID an (?id=...).</p>",
        )
        return HTMLResponse(content=html)

    record = deletion_store.get_status(code)
    if record is None:
        html = _status_page_html(
            "Nicht gefunden",
            "<p>Kein Eintrag mit dieser Confirmation-ID gefunden.</p>",
        )
        return HTMLResponse(content=html, status_code=404)

    html = _status_page_html(
        "Data Deletion Status",
        f"<p><strong>Confirmation Code:</strong> {record['confirmation_code']}</p>"
        f"<p><strong>Status:</strong> {record['status']}</p>"
        f"<p><strong>Angefordert am:</strong> {record['requested_at']}</p>",
    )
    return HTMLResponse(content=html)
