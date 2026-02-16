from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from database import init_db, is_msg_processed, delete_user_data
from email_service import send_privacy_email
from cleanup import run_scheduler
from logic import handle_message
from config import Config
import asyncio
import hashlib
import hmac
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.on_event("startup")
async def startup():
    init_db()
    asyncio.create_task(run_scheduler())

@app.get("/webhook")
async def verify(request: Request):
    if request.query_params.get("hub.verify_token") == Config.VERIFY_TOKEN:
        return Response(content=request.query_params.get("hub.challenge"))
    return Response(status_code=403)

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    
    try:
        changes = data.get("entry", [])[0].get("changes", [])[0]
        value = changes.get("value", {})
        
        if "messages" in value:
            message = value["messages"][0]
            phone = message["from"] # Format: 49176...
            msg_id = message["id"]
            
            # 1. Profil-Namen extrahieren
            profile_name = "Gast"
            contacts = value.get("contacts", [])
            if contacts:
                profile_name = contacts[0].get("profile", {}).get("name", "Gast")

            # 2. Textinhalt extrahieren
            text = ""
            if "interactive" in message:
                if "button_reply" in message["interactive"]:
                    text = message["interactive"]["button_reply"]["title"]
                elif "list_reply" in message["interactive"]:
                    text = message["interactive"]["list_reply"]["title"]
            elif "text" in message:
                text = message["text"]["body"]

            # 3. An Logik übergeben
            if text and not is_msg_processed(msg_id):
                await handle_message(phone, text, msg_id, profile_name)
                
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
    
    return {"status": "ok"}

@app.post("/data-deletion")
async def data_deletion(request: Request):
    body = await request.body()
    data = json.loads(body)

    signed_request = data.get("signed_request", "")
    parts = signed_request.split(".", 1)
    if len(parts) != 2:
        return Response(status_code=400)

    encoded_sig, payload = parts
    # Decode und verifiziere Signatur
    import base64
    sig = base64.urlsafe_b64decode(encoded_sig + "==")
    expected_sig = hmac.new(
        Config.APP_SECRET.encode(), payload.encode(), hashlib.sha256
    ).digest()

    if not hmac.compare_digest(sig, expected_sig):
        return Response(status_code=403)

    decoded = json.loads(base64.urlsafe_b64decode(payload + "=="))
    user_id = decoded.get("user_id")

    if user_id:
        lead_data = delete_user_data(user_id)
        if lead_data:
            lead_data["phone"] = user_id
            lead_data["trigger"] = "Meta data-deletion callback"
            await send_privacy_email("deletion_request", lead_data)

    confirmation_code = hashlib.sha256(f"{user_id}-deleted".encode()).hexdigest()[:12]
    return JSONResponse({
        "url": f"{Config.BASE_URL}/deletion-status?code={confirmation_code}",
        "confirmation_code": confirmation_code
    })
