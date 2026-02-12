import json
import os
from string import Template
from config import Config

# Cache für Sprachdateien
_LANG_CACHE = {}

def load_languages():
    """Lädt alle .json Dateien aus dem lang/ Ordner"""
    if not os.path.exists(Config.LANG_DIR):
        os.makedirs(Config.LANG_DIR)
        return

    for filename in os.listdir(Config.LANG_DIR):
        if filename.endswith(".json"):
            lang_code = filename.split(".")[0]
            try:
                with open(os.path.join(Config.LANG_DIR, filename), "r", encoding="utf-8") as f:
                    _LANG_CACHE[lang_code] = json.load(f)
            except Exception as e:
                print(f"Error loading language {filename}: {e}")

# Init beim Start
load_languages()

def detect_language(phone_number):
    """Simple Mapping basierend auf Vorwahl"""
    if phone_number.startswith("49"): return "de"
    if phone_number.startswith("43"): return "de" # Österreich
    if phone_number.startswith("41"): return "de" # Schweiz
    if phone_number.startswith("1"): return "en"  # USA/Canada
    return "en" # Default Fallback

def get_msg(key, lang="en", **kwargs):
    """
    Holt Nachricht und ersetzt Platzhalter ($NAME, etc.).
    Fallback auf 'en', wenn Sprache oder Key nicht existiert.
    """
    # 1. Versuch: Gewünschte Sprache
    data = _LANG_CACHE.get(lang)
    if not data:
        data = _LANG_CACHE.get("en", {})
    
    raw_msg = data.get("messages", {}).get(key)
    
    # 2. Fallback: Englisch
    if not raw_msg and lang != "en":
         raw_msg = _LANG_CACHE.get("en", {}).get("messages", {}).get(key)
    
    if not raw_msg:
        return f"[MISSING TEXT: {key}]"
    
    # Platzhalter ersetzen (füge Config-Vars global hinzu)
    kwargs["OWNER_NAME"] = Config.OWNER_NAME
    kwargs["EMAIL"] = Config.CONTACT_EMAIL
    kwargs["WEBSITE"] = Config.WEBSITE
    
    return Template(raw_msg).safe_substitute(**kwargs)

def resolve_command(text, lang="en"):
    """
    Prüft input gegen ENGLISCH (immer aktiv) und LOKALSPRACHE.
    Gibt den Canonical Command zurück (z.B. 'START') oder None.
    """
    text = text.lower().strip().replace("/", "")
    
    # Prüfe erst Englisch (Global)
    en_cmds = _LANG_CACHE.get("en", {}).get("commands", {})
    for cmd_key, aliases in en_cmds.items():
        if text in aliases:
            return cmd_key
            
    # Prüfe Lokalsprache
    if lang != "en":
        loc_cmds = _LANG_CACHE.get(lang, {}).get("commands", {})
        for cmd_key, aliases in loc_cmds.items():
            if text in aliases:
                return cmd_key
                
    return None
