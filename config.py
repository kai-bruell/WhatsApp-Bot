import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Meta API
    WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
    PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
    VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
    
    # Owner Info
    OWNER_NAME = os.getenv("OWNER_NAME", "Alexander")
    CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "mail@example.com")
    WEBSITE = os.getenv("WEBSITE", "www.example.com")
    
    # Paths
    DB_PATH = os.getenv("DB_PATH", "data/bot.db")
    LANG_DIR = os.getenv("LANG_DIR", "lang")
