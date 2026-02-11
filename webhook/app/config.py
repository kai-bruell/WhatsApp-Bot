import os
from pathlib import Path

from dotenv import load_dotenv

# .env nur laden, wenn Datei existiert (lokale Entwicklung).
# In Docker werden Env-Vars via docker-compose injiziert.
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    load_dotenv(_env_file)

# --- Meta / WhatsApp API ---
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "MeinSuperGeheimerDevOpsToken123")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "DEIN_SYSTEM_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "953289931205420")
APP_SECRET = os.getenv("APP_SECRET", "")
META_API_VERSION = "v18.0"
META_API_URL = f"https://graph.facebook.com/{META_API_VERSION}/{PHONE_NUMBER_ID}/messages"

# --- Kontaktdaten (Willkommensnachricht) ---
CONTACT_MOBILE = os.getenv("CONTACT_MOBILE", "123456789")
CONTACT_LANDLINE = os.getenv("CONTACT_LANDLINE", "0011223344")
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "Assistenz@meine-mail.com")

# --- Base URL (fuer Links in Bot-Nachrichten) ---
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# --- Radicale (CardDAV) ---
RADICALE_URL = os.getenv("RADICALE_URL", "http://localhost:5232")
RADICALE_USER = os.getenv("RADICALE_USER", "bot_user")
RADICALE_PASSWORD = os.getenv("RADICALE_PASSWORD", "passwort")
RADICALE_ADDRESSBOOK = "contacts"

# --- Rate Limits ---
RATE_SMS_PER_USER_DAY = int(os.getenv("RATE_SMS_PER_USER_DAY", "10"))
RATE_SMS_GLOBAL_DAY = int(os.getenv("RATE_SMS_GLOBAL_DAY", "100"))
RATE_EMAIL_PER_USER_DAY = int(os.getenv("RATE_EMAIL_PER_USER_DAY", "10"))
RATE_EMAIL_GLOBAL_DAY = int(os.getenv("RATE_EMAIL_GLOBAL_DAY", "300"))
RATE_API_GLOBAL_HOUR = int(os.getenv("RATE_API_GLOBAL_HOUR", "300"))
RATE_API_PER_USER_HOUR = int(os.getenv("RATE_API_PER_USER_HOUR", "10"))

# --- Rate Limit DB ---
RATE_LIMIT_DB = os.getenv("RATE_LIMIT_DB", "/app/data/rate_limit.db")
