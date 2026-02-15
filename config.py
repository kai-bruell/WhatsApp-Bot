import os
from dotenv import load_dotenv

load_dotenv()

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

    # Paths
    DB_PATH = os.getenv("DB_PATH", "data/bot.db")
    LANG_DIR = os.getenv("LANG_DIR", "lang")
