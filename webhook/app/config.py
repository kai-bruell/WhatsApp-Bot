import os
from pathlib import Path

from dotenv import load_dotenv

# .env aus dem webhook-Verzeichnis laden
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# --- Meta / WhatsApp API ---
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "MeinSuperGeheimerDevOpsToken123")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "DEIN_SYSTEM_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "953289931205420")
META_API_VERSION = "v18.0"
META_API_URL = f"https://graph.facebook.com/{META_API_VERSION}/{PHONE_NUMBER_ID}/messages"

# --- Radicale (CardDAV) ---
RADICALE_URL = os.getenv("RADICALE_URL", "http://localhost:5232")
RADICALE_USER = os.getenv("RADICALE_USER", "bot_user")
RADICALE_PASSWORD = os.getenv("RADICALE_PASSWORD", "passwort")
RADICALE_ADDRESSBOOK = "contacts"
