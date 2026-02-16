import os
import re
from dotenv import load_dotenv

load_dotenv()

def parse_duration(s, default_seconds=30*86400):
    """Parse duration string like '30d', '1d12h', '0d0h5m30s' to seconds.
    Falls back to interpreting as days (int) for backwards compat."""
    if not s:
        return default_seconds
    try:
        return int(s) * 86400
    except ValueError:
        pass
    m = re.fullmatch(r'(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?', s.strip())
    if not m or not any(m.groups()):
        return default_seconds
    d, h, mi, sec = (int(g or 0) for g in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + sec

class Config:
    # Meta API
    WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
    PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
    VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
    APP_SECRET = os.getenv("APP_SECRET")
    BASE_URL = os.getenv("BASE_URL", "https://localhost")
    
    # Owner Info
    OWNER_NAME = os.getenv("OWNER_NAME", "Alexander")
    CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "mail@example.com")
    WEBSITE = os.getenv("WEBSITE", "www.example.com")
    
    # SMTP
    SMTP_HOST = os.getenv("SMTP_HOST")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASS = os.getenv("SMTP_PASS")
    SMTP_FROM = os.getenv("SMTP_FROM")
    SMTP_VERIFY_TLS = os.getenv("SMTP_VERIFY_TLS", "true").lower() == "true"

    # Privacy
    PRIVACY_EMAIL = os.getenv("PRIVACY_EMAIL")
    DATA_RETENTION_SECONDS = parse_duration(os.getenv("DATA_RETENTION_TIME", "30d"))
    CLEANUP_INTERVAL_SECONDS = parse_duration(os.getenv("CLEANUP_INTERVAL", "1h"), default_seconds=3600)

    # Paths
    DB_PATH = os.getenv("DB_PATH", "data/bot.db")
    LANG_DIR = os.getenv("LANG_DIR", "lang")
