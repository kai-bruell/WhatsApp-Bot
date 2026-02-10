# DOKUMENTATION FÜR EINE ANTWORT

import httpx
from fastapi import FastAPI, Request

app = FastAPI()

TOKEN = "DEIN_SYSTEM_TOKEN"
PN_ID = "953289931205420"
URL = f"https://graph.facebook.com/v18.0/{PN_ID}/messages"

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    
    try:
        # Extrahiere Daten aus dem JSON
        val = data['entry'][0]['changes'][0]['value']
        if 'messages' in val:
            number = val['messages'][0]['from']
            text = val['messages'][0]['text']['body']
            
            # Hier KI-Logik einfügen - aktuell Echo
            await send_msg(number, f"Echo: {text}")
            
    except KeyError:
        pass
    
    return {"status": "ok"}

async def send_msg(to, text):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    async with httpx.AsyncClient() as client:
        await client.post(URL, headers=headers, json=payload)

# Webhook-Handshake (GET) muss drin bleiben für Meta-Checks
@app.get("/webhook")
async def verify(request: Request):
    params = request.query_params
    return int(params.get("hub.challenge"))
