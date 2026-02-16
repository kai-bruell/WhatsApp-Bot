import httpx
import re
import asyncio
from config import Config
from database import get_session, update_session, get_db, clear_session, log_sent_email, delete_user_data
from localization import get_msg, resolve_command, detect_language
from email_service import send_lead_email, send_privacy_email

URL = f"https://graph.facebook.com/v18.0/{Config.PHONE_NUMBER_ID}/messages"

# --- Helper ---
async def send_wa(to, text, buttons=None):
    headers = {
        "Authorization": f"Bearer {Config.WHATSAPP_TOKEN}", 
        "Content-Type": "application/json"
    }
    
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
        for b_text in buttons:
            # ID safe machen und Länge begrenzen
            b_id = re.sub(r'\W+', '', b_text)[:20]
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
    step, ctx, lang = get_session(phone)
    
    if not lang:
        lang = detect_language(phone)
        update_session(phone, step, ctx, lang)

    text_clean = text.strip()
    command = resolve_command(text_clean, lang)
    
    # --- Globale Befehle ---
    if command == "STOP":
        clear_session(phone)
        return await send_wa(phone, get_msg("stop_msg", lang))
    
    if command == "CONTACT":
        return await send_wa(phone, get_msg("menu_contact_text", lang))

    if command == "PRIVACY":
        btns = [get_msg("btn_delete_yes", lang), get_msg("btn_delete_no", lang)]
        await send_wa(phone, get_msg("privacy_confirm", lang), btns)
        update_session(phone, "CONFIRM_DELETE", ctx, lang)
        return

    if command == "START":
        step = "START"
        ctx = {}

    if command == "HELP":
        step = "START"

    # --- State Machine ---
    match step:
        case "START":
            ctx["profile_name"] = profile_name
            if text_clean == get_msg("btn_msg", lang):
                await send_wa(phone, get_msg("menu_prompt", lang))
                update_session(phone, "ASK_REASON", ctx, lang)
            else:
                msg = get_msg("welcome", lang, NAME=profile_name)
                btns = [get_msg("btn_msg", lang), get_msg("btn_contact", lang)]
                await send_wa(phone, msg, btns)
                update_session(phone, "MENU_SELECTION", ctx, lang)

        case "MENU_SELECTION":
            if text_clean == get_msg("btn_msg", lang):
                await send_wa(phone, get_msg("menu_prompt", lang))
                update_session(phone, "ASK_REASON", ctx, lang)
            elif text_clean == get_msg("btn_contact", lang):
                await send_wa(phone, get_msg("menu_contact_text", lang))
                update_session(phone, "START", {}, lang)
            else:
                ctx["reason"] = text_clean
                await process_name_check(phone, ctx, lang)

        case "ASK_REASON":
            if text_clean == get_msg("btn_contact", lang):
                await send_wa(phone, get_msg("menu_contact_text", lang))
                await send_wa(phone, get_msg("menu_prompt", lang))
            else:
                ctx["reason"] = text_clean
                await process_name_check(phone, ctx, lang)

        case "CONFIRM_NAME":
            if text_clean == get_msg("btn_yes_correct", lang):
                ctx["name"] = ctx.get("profile_name")
                await ask_email_step(phone, ctx, lang)
            elif text_clean == get_msg("btn_change_name", lang):
                await send_wa(phone, get_msg("ask_name_manual", lang))
                update_session(phone, "ASK_NAME_MANUAL", ctx, lang)
            elif text_clean == get_msg("btn_cancel", lang):
                clear_session(phone)
                await send_wa(phone, get_msg("stop_msg", lang))
            else:
                ctx["name"] = text_clean
                await ask_email_step(phone, ctx, lang)

        case "ASK_NAME_MANUAL":
            ctx["name"] = text_clean
            await ask_email_step(phone, ctx, lang)

        case "ASK_EMAIL":
            email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text_clean)
            if email_match:
                ctx["email"] = email_match.group(0)
                
                # Zusammenfassung senden
                summary = get_msg("summary", lang, NAME=ctx['name'], USER_EMAIL=ctx['email'], REASON=ctx['reason'])
                await send_wa(phone, summary)
                await asyncio.sleep(0.5)
                
                # --- NEU: Einfache Telefonnummer Abfrage ---
                # Buttons: "Ja, WA-Nummer", "Andere Nummer", "Nein"
                btn_wa = get_msg("btn_use_wa_num", lang, PHONE=phone)
                btn_other = get_msg("btn_type_num", lang)
                btn_no = get_msg("btn_no_num", lang)

                prompt = get_msg("ask_phone_optin", lang)

                await send_wa(phone, prompt, [btn_wa, btn_other, btn_no])
                update_session(phone, "ASK_PHONE_DECISION", ctx, lang)
            else:
                await send_wa(phone, get_msg("email_invalid", lang))

        case "ASK_PHONE_DECISION":
            btn_wa = get_msg("btn_use_wa_num", lang, PHONE=phone)
            btn_other = get_msg("btn_type_num", lang)
            btn_no = get_msg("btn_no_num", lang)

            # Option 1: WhatsApp Nummer übernehmen
            if text_clean == btn_wa:
                ctx["contact_number"] = phone
                await finalize_lead(phone, ctx, lang)

            # Option 2: Andere Nummer eingeben
            elif text_clean == btn_other:
                await send_wa(phone, get_msg("ask_new_phone", lang))
                update_session(phone, "ASK_PHONE_MANUAL", ctx, lang)

            # Option 3: Keine Nummer
            elif text_clean == btn_no:
                ctx["contact_number"] = None
                await finalize_lead(phone, ctx, lang)

            else:
                # Loop bei falscher Eingabe
                await send_wa(phone, get_msg("ask_phone_optin", lang), [btn_wa, btn_other, btn_no])

        case "ASK_PHONE_MANUAL":
            # Simple Bereinigung
            potential_num = text_clean.replace(" ", "").replace("-", "")
            
            # Grober Check: Mindestens 7 Ziffern
            if len(potential_num) > 6 and re.search(r'\d', potential_num):
                ctx["contact_number"] = potential_num
                await finalize_lead(phone, ctx, lang)
            else:
                await send_wa(phone, get_msg("phone_invalid", lang))

        case "CONFIRM_DELETE":
            if text_clean == get_msg("btn_delete_yes", lang):
                lead_data = delete_user_data(phone)
                if lead_data:
                    lead_data["phone"] = phone
                    lead_data["trigger"] = "User via /datenschutz bot command"
                    await send_privacy_email("deletion_request", lead_data)
                    await send_wa(phone, get_msg("privacy_deleted", lang))
                else:
                    await send_wa(phone, get_msg("privacy_no_data", lang))
            else:
                await send_wa(phone, get_msg("privacy_cancelled", lang))
                clear_session(phone)

        case "COMPLETED":
            await send_wa(phone, get_msg("completed_hint", lang))

async def ask_email_step(phone, ctx, lang):
    """Helper um Wiederholungen zu vermeiden"""
    await send_wa(phone, get_msg("ask_email", lang))
    update_session(phone, "ASK_EMAIL", ctx, lang)

async def process_name_check(phone, ctx, lang):
    p_name = ctx.get("profile_name", "Gast")
    msg = get_msg("ask_name_confirm", lang, NAME=p_name)
    btns = [get_msg("btn_yes_correct", lang), get_msg("btn_change_name", lang), get_msg("btn_cancel", lang)]
    await send_wa(phone, msg, btns)
    update_session(phone, "CONFIRM_NAME", ctx, lang)

async def finalize_lead(phone, ctx, lang):
    db = get_db()
    contact_num = ctx.get("contact_number")
    
    # SMS_OPTIN ist jetzt 0 (wir senden keine SMS)
    # CALL_OPTIN ist 1, wenn eine Nummer hinterlegt wurde
    call_optin = 1 if contact_num else 0
    
    db.execute("""
        INSERT OR REPLACE INTO leads
        (phone, name, email, reason, sms_number, sms_optin, call_optin, language, status)
        VALUES (?, ?, ?, ?, ?, 0, ?, ?, 'new')
    """, (phone, ctx.get("name"), ctx.get("email"), ctx.get("reason"), contact_num, call_optin, lang))
    db.commit()

    # Session SOFORT auf COMPLETED setzen, BEVOR async-Operationen starten.
    # Verhindert dass ein zweiter Webhook während send_lead_email()
    # nochmal finalize_lead auslöst (Race-Condition).
    update_session(phone, "COMPLETED", {}, lang)

    ok, reason = await send_lead_email(ctx, lang)
    if ok:
        log_sent_email(phone, ctx.get("name"), ctx.get("email"), ctx.get("reason"))
    else:
        await send_wa(phone, get_msg("email_send_failed", lang, REASON=reason))

    await send_wa(phone, get_msg("final_success", lang, NAME=ctx.get("name")))
