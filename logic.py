import httpx
import re
import asyncio
from config import Config
from database import get_session, update_session, get_db, clear_session
from localization import get_msg, resolve_command, detect_language

URL = f"https://graph.facebook.com/v18.0/{Config.PHONE_NUMBER_ID}/messages"

# --- Helper ---
async def send_wa(to, text, buttons=None):
    headers = {
        "Authorization": f"Bearer {Config.WHATSAPP_TOKEN}", 
        "Content-Type": "application/json"
    }
    
    # Text abschneiden falls > 4096 (WhatsApp Limit), sicherheitshalber
    text = text[:4090]
    
    payload = {
        "messaging_product": "whatsapp", 
        "to": to, 
        "type": "text", 
        "text": {"body": text}
    }
    
    if buttons:
        payload["type"] = "interactive"
        payload["interactive"] = {
            "type": "button",
            "body": {"text": text},
            "action": {"buttons": []}
        }
        # Buttons dynamisch bauen (ID = Titel gekürzt)
        for b_text in buttons:
            b_id = re.sub(r'\W+', '', b_text)[:20] # ID safe machen
            payload["interactive"]["action"]["buttons"].append({
                "type": "reply", 
                "reply": {"id": b_id, "title": b_text[:20]}
            })
    
    async with httpx.AsyncClient() as client:
        try:
            await client.post(URL, headers=headers, json=payload)
        except Exception as e:
            print(f"Failed to send WA: {e}")

# --- Main Logic ---
async def handle_message(phone, text, msg_id, profile_name="Gast"):
    # 1. Session & Sprache laden
    step, ctx, lang = get_session(phone)
    
    # Wenn User neu ist (lang=None), Sprache detektieren
    if not lang:
        lang = detect_language(phone)
        # Session initialisieren
        update_session(phone, step, ctx, lang)

    text_clean = text.strip()
    
    # 2. Command Parsing (Global & Lokal)
    command = resolve_command(text_clean, lang)
    
    # --- Globale Befehle ---
    if command == "STOP":
        clear_session(phone)
        return await send_wa(phone, get_msg("stop_msg", lang))
    
    if command == "CONTACT":
        msg = get_msg("menu_contact_text", lang)
        return await send_wa(phone, msg)
        
    if command == "START":
        # Force Reset
        step = "START"
        ctx = {}
    
    if command == "HELP":
        # Hilfe ist im Welcome Text enthalten, also Neustart simulieren
        step = "START"

    # --- State Machine ---
    match step:
        case "START":
            ctx["profile_name"] = profile_name
            
            # Willkommensnachricht mit Befehlsübersicht
            msg = get_msg("welcome", lang, NAME=profile_name)
            
            # Buttons laden
            btns = [get_msg("btn_msg", lang), get_msg("btn_contact", lang)]
            
            await send_wa(phone, msg, btns)
            update_session(phone, "MENU_SELECTION", ctx, lang)

        case "MENU_SELECTION":
            # Check Button Replies via Text (oder fuzzy matching)
            if text_clean == get_msg("btn_msg", lang):
                await send_wa(phone, get_msg("menu_prompt", lang))
                update_session(phone, "ASK_REASON", ctx, lang)
                
            elif text_clean == get_msg("btn_contact", lang):
                await send_wa(phone, get_msg("menu_contact_text", lang))
                # Hiernach zurücksetzen auf Start
                update_session(phone, "START", {}, lang)
            else:
                # Fallback: Wenn User Text schreibt statt Button zu klicken -> Als Grund werten
                ctx["reason"] = text_clean
                await process_name_check(phone, ctx, lang)

        case "ASK_REASON":
            ctx["reason"] = text_clean
            await process_name_check(phone, ctx, lang)

        case "CONFIRM_NAME":
            if text_clean == get_msg("btn_yes_correct", lang):
                ctx["name"] = ctx.get("profile_name")
                await send_wa(phone, get_msg("ask_email", lang))
                update_session(phone, "ASK_EMAIL", ctx, lang)
                
            elif text_clean == get_msg("btn_change_name", lang):
                await send_wa(phone, get_msg("ask_name_manual", lang))
                update_session(phone, "ASK_NAME_MANUAL", ctx, lang)
                
            elif text_clean == get_msg("btn_cancel", lang):
                clear_session(phone)
                await send_wa(phone, get_msg("stop_msg", lang))
            else:
                # Freitext Eingabe als Name werten
                ctx["name"] = text_clean
                await send_wa(phone, get_msg("ask_email", lang))
                update_session(phone, "ASK_EMAIL", ctx, lang)

        case "ASK_NAME_MANUAL":
            ctx["name"] = text_clean
            await send_wa(phone, get_msg("ask_email", lang))
            update_session(phone, "ASK_EMAIL", ctx, lang)

        case "ASK_EMAIL":
            # Einfache Email Regex
            email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text_clean)
            if email_match:
                ctx["email"] = email_match.group(0)
                
                # Zusammenfassung senden
                summary = get_msg("summary", lang, NAME=ctx['name'], EMAIL=ctx['email'], REASON=ctx['reason'])
                await send_wa(phone, summary)
                await asyncio.sleep(0.5)
                
                # SMS Opt-In Abfrage
                # Frage: Darf ich SMS senden? -> Buttons: 1. Ja an +1234, 2. Andere Nummer, 3. Nein
                btn_yes = get_msg("btn_sms_current", lang, PHONE=phone)
                btn_other = get_msg("btn_sms_other", lang)
                btn_no = get_msg("btn_no_sms", lang)
                
                prompt = get_msg("ask_sms_optin", lang)
                
                await send_wa(phone, prompt, [btn_yes, btn_other, btn_no])
                update_session(phone, "ASK_SMS_DECISION", ctx, lang)
            else:
                await send_wa(phone, get_msg("email_invalid", lang))

        case "ASK_SMS_DECISION":
            btn_yes = get_msg("btn_sms_current", lang, PHONE=phone) # Müssen Text vergleichen
            btn_other = get_msg("btn_sms_other", lang)
            btn_no = get_msg("btn_no_sms", lang)

            # Button 1: Aktuelle Nummer
            if text_clean == btn_yes or "1" in text_clean: # Tolerant für "1" Eingabe
                await finalize_lead(phone, ctx, lang, sms_optin=True, sms_number=phone)
            
            # Button 2: Andere Nummer
            elif text_clean == btn_other:
                await send_wa(phone, get_msg("ask_new_phone", lang))
                update_session(phone, "ASK_NEW_PHONE_NUMBER", ctx, lang)
            
            # Button 3: Nein
            elif text_clean == btn_no:
                await finalize_lead(phone, ctx, lang, sms_optin=False, sms_number=None)
            
            else:
                # Fallback -> Als "Andere Nummer" Eingabe werten, wenn es wie eine Nummer aussieht?
                # Besser: Wiederhole Frage
                 await send_wa(phone, get_msg("ask_sms_optin", lang), [btn_yes, btn_other, btn_no])

        case "ASK_NEW_PHONE_NUMBER":
            # Validierung (sehr simpel, kann verbessert werden)
            # Entferne Spaces und Striche
            potential_num = text_clean.replace(" ", "").replace("-", "")
            
            if len(potential_num) > 7 and (potential_num.startswith("+") or potential_num.startswith("00")):
                await finalize_lead(phone, ctx, lang, sms_optin=True, sms_number=potential_num)
            else:
                await send_wa(phone, get_msg("phone_invalid", lang))

        case "COMPLETED":
            await send_wa(phone, get_msg("completed_hint", lang))

async def process_name_check(phone, ctx, lang):
    """Helper, um den Flow zur Namensbestätigung zu leiten"""
    p_name = ctx.get("profile_name", "Gast")
    msg = get_msg("ask_name_confirm", lang, NAME=p_name)
    
    btns = [
        get_msg("btn_yes_correct", lang), 
        get_msg("btn_change_name", lang), 
        get_msg("btn_cancel", lang)
    ]
    await send_wa(phone, msg, btns)
    update_session(phone, "CONFIRM_NAME", ctx, lang)

async def finalize_lead(phone, ctx, lang, sms_optin, sms_number):
    db = get_db()
    db.execute("""
        INSERT OR REPLACE INTO leads 
        (phone, name, email, reason, sms_number, sms_optin, language, status) 
        VALUES (?, ?, ?, ?, ?, ?, ?, 'new')
    """, (phone, ctx.get("name"), ctx.get("email"), ctx.get("reason"), sms_number, 1 if sms_optin else 0, lang))
    db.commit()
    
    await send_wa(phone, get_msg("final_success", lang, NAME=ctx.get("name")))
    update_session(phone, "COMPLETED", {}, lang)
