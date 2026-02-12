from fastapi import FastAPI, Request, Response
from database import init_db, is_msg_processed
from logic import handle_message
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.on_event("startup")
def startup():
    init_db()

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
