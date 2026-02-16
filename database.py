import sqlite3
import json
from datetime import datetime, timedelta
from config import Config

def get_db():
    conn = sqlite3.connect(Config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()

    db.execute("PRAGMA journal_mode=WAL")

    # Sessions: Jetzt mit 'language'
    db.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            phone TEXT PRIMARY KEY,
            step TEXT,
            context TEXT,
            language TEXT DEFAULT 'en',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migration: updated_at nachrüsten falls Tabelle schon existiert
    try:
        db.execute("ALTER TABLE sessions ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP")
    except sqlite3.OperationalError:
        pass  # Spalte existiert bereits
    
    # Leads
    db.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            phone TEXT PRIMARY KEY,
            name TEXT,
            email TEXT,
            reason TEXT,
            sms_number TEXT,
            sms_optin INTEGER DEFAULT 0,
            call_optin INTEGER DEFAULT 0,
            status TEXT DEFAULT 'new',
            language TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migration: call_optin nachrüsten falls Tabelle schon existiert
    try:
        db.execute("ALTER TABLE leads ADD COLUMN call_optin INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    
    db.execute("CREATE TABLE IF NOT EXISTS processed_messages (msg_id TEXT PRIMARY KEY, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")

    # Email Log für DSGVO-Tracking
    db.execute("""
        CREATE TABLE IF NOT EXISTS email_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            lead_name TEXT,
            lead_email TEXT,
            reason TEXT,
            sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            delete_by DATETIME,
            deletion_requested INTEGER DEFAULT 0,
            deletion_requested_at DATETIME
        )
    """)

    db.commit()

def is_msg_processed(msg_id):
    db = get_db()
    try:
        db.execute("INSERT INTO processed_messages (msg_id) VALUES (?)", (msg_id,))
        db.commit()
        return False
    except sqlite3.IntegrityError:
        return True

def get_session(phone):
    res = get_db().execute("SELECT step, context, language FROM sessions WHERE phone = ?", (phone,)).fetchone()
    if res:
        return res["step"], json.loads(res["context"]), res["language"]
    return "START", {}, None # None = Sprache noch nicht gesetzt

def update_session(phone, step, context, language=None):
    db = get_db()
    # Bestehende Sprache holen, falls language=None
    if language is None:
        curr = db.execute("SELECT language FROM sessions WHERE phone = ?", (phone,)).fetchone()
        language = curr["language"] if curr else "en"
        
    db.execute("INSERT OR REPLACE INTO sessions VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
               (phone, step, json.dumps(context), language))
    db.commit()

def clear_session(phone):
    # Reset auf START, behalte aber Sprache bei, wenn möglich
    _, _, lang = get_session(phone)
    update_session(phone, "START", {}, lang or "en")

def log_sent_email(phone, name, email, reason):
    db = get_db()
    delete_by = (datetime.utcnow() + timedelta(seconds=Config.DATA_RETENTION_SECONDS)).strftime("%Y-%m-%d %H:%M:%S")
    db.execute(
        "INSERT INTO email_log (phone, lead_name, lead_email, reason, delete_by) VALUES (?, ?, ?, ?, ?)",
        (phone, name, email, reason, delete_by)
    )
    db.commit()

def mark_deletion_requested(phone):
    db = get_db()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    db.execute(
        "UPDATE email_log SET deletion_requested = 1, deletion_requested_at = ? WHERE phone = ?",
        (now, phone)
    )
    db.commit()

def delete_user_data(phone):
    db = get_db()
    # Lead-Daten holen bevor sie gelöscht werden
    lead = db.execute("SELECT name, email, reason FROM leads WHERE phone = ?", (phone,)).fetchone()
    lead_data = dict(lead) if lead else None

    db.execute("DELETE FROM sessions WHERE phone = ?", (phone,))
    db.execute("DELETE FROM leads WHERE phone = ?", (phone,))
    mark_deletion_requested(phone)
    db.commit()

    return lead_data
