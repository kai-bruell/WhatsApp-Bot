"""
Bot-Logik: Steuert den Gespraechsfluss.

Die eigentliche Geschaeftslogik (vCard, Radicale, SMS-Versand) ist noch
Platzhalter — der Bot antwortet aber bereits mit echten WhatsApp-Nachrichten.
"""

import re

from app.messenger import send_text, send_interactive_buttons
from app.vcard import create_vcard
from app.radicale import sync_contact
from app.i18n import t, detect_lang
from app.config import CONTACT_MOBILE, CONTACT_LANDLINE, CONTACT_EMAIL

# ---------------------------------------------------------------------------
# User-State: trackt pro Sender, in welchem Schritt er sich befindet.
# ---------------------------------------------------------------------------
user_state: dict[str, dict] = {}
# Moegliche States:
# {"step": "awaiting_phone"}                               — Rueckruf: Nummer erwartet
# {"step": "awaiting_message", "channel": "sms"|"email"}   — Nachricht erwartet
# {"step": "confirm_message", "channel": ..., "text": ...} — Bestaetigung erwartet

_PHONE_RE = re.compile(r"^\+?\d[\d\s\-/]{6,18}\d$")


# ---------------------------------------------------------------------------
# Validierung
# ---------------------------------------------------------------------------

def _validate_sms(text: str, lang: str) -> list[str]:
    """Prueft GSM-7-Kompatibilitaet und Zeichenlimit. Gibt Fehlerliste zurueck."""
    errors: list[str] = []
    gsm7_pattern = re.compile(
        r"^[\w\s\d.,!@#$%^&*()\-=+\[\]{};:'\"<>?/\\|~\n\r]*$"
    )
    is_gsm7 = bool(gsm7_pattern.match(text))
    limit = 160 if is_gsm7 else 70

    if not is_gsm7:
        errors.append(t("illegal_chars", lang))
    if len(text) > limit:
        errors.append(t("char_limit_exceeded", lang, count=len(text), limit=limit))
    return errors


# ---------------------------------------------------------------------------
# Private Flow-Funktionen
# ---------------------------------------------------------------------------

async def _process_phone_number(sender: str, text: str) -> None:
    """Validiert eine eingegebene Rufnummer."""
    lang = detect_lang(sender)
    cleaned = text.strip()
    if not _PHONE_RE.match(cleaned):
        await send_text(sender, t("invalid_phone", lang))
        return  # State bleibt auf awaiting_phone

    # Erfolg
    user_state.pop(sender, None)
    print(f"[STUB] Rueckruf an {cleaned} wird veranlasst.")
    await send_interactive_buttons(
        sender,
        t("callback_initiated", lang, phone=cleaned),
        [
            {"id": "btn_more", "title": t("btn_more_title", lang)},
            {"id": "btn_end", "title": t("btn_end_title", lang)},
        ],
    )


async def _process_message_text(sender: str, text: str) -> None:
    """Validiert eine eingegebene Nachricht (SMS/Email)."""
    lang = detect_lang(sender)
    state = user_state[sender]
    channel = state["channel"]

    if channel == "sms":
        errors = _validate_sms(text, lang)
        if errors:
            msg = "\n".join(errors)
            await send_interactive_buttons(
                sender,
                t("validation_failed", lang, errors=msg),
                [
                    {"id": "btn_new_message", "title": t("btn_new_message_title", lang)},
                    {"id": "btn_cancel", "title": t("btn_cancel_title", lang)},
                ],
            )
            return  # State bleibt auf awaiting_message

    # Validierung bestanden (oder Email — keine Einschraenkung)
    user_state[sender] = {
        "step": "confirm_message",
        "channel": channel,
        "text": text,
    }
    label = t("label_sms", lang) if channel == "sms" else t("label_email", lang)
    await send_interactive_buttons(
        sender,
        t("confirm_message", lang, label=label, text=text),
        [
            {"id": "btn_send", "title": t("btn_send_title", lang)},
            {"id": "btn_new_message", "title": t("btn_new_message_title", lang)},
            {"id": "btn_cancel", "title": t("btn_cancel_title", lang)},
        ],
    )


async def _send_completion(sender: str) -> None:
    """Sendet den Abschluss-Flow und loescht den State."""
    lang = detect_lang(sender)
    user_state.pop(sender, None)
    await send_interactive_buttons(
        sender,
        t("message_sent", lang),
        [
            {"id": "btn_more", "title": t("btn_more_title", lang)},
            {"id": "btn_end", "title": t("btn_end_title", lang)},
        ],
    )


# ---------------------------------------------------------------------------
# Oeffentliche Handler
# ---------------------------------------------------------------------------

async def handle_incoming_message(message: dict, contact_info: dict) -> None:
    """Zentraler Einstiegspunkt fuer jede eingehende Nachricht."""
    sender = message.get("from", "unbekannt")
    msg_type = message.get("type", "unknown")
    contact_name = contact_info.get("profile", {}).get("name", "Unbekannt")
    lang = detect_lang(sender)

    print(f"[BOT] Nachricht von {sender} ({contact_name}), Typ: {msg_type}")

    # --- Textnachricht ---
    if msg_type == "text":
        text = message["text"]["body"]
        await handle_text_message(sender, contact_name, text)

    # --- Button-Klick (Interactive) ---
    elif msg_type == "interactive":
        interactive = message.get("interactive", {})
        if "button_reply" in interactive:
            button_id = interactive["button_reply"]["id"]
            await handle_button_reply(sender, contact_name, button_id)
        elif "list_reply" in interactive:
            list_id = interactive["list_reply"]["id"]
            await handle_list_reply(sender, contact_name, list_id)

    # --- Medien / Anhang ---
    elif msg_type in ("image", "document", "audio", "video", "sticker"):
        # Caption extrahieren (image, video, document koennen Captions haben)
        caption = message.get(msg_type, {}).get("caption")
        await handle_attachment(sender, msg_type, caption)

    else:
        print(f"[BOT] Unbekannter Nachrichtentyp: {msg_type}")
        await send_interactive_buttons(
            sender,
            t("unsupported_type", lang),
            [
                {"id": "btn_new_message", "title": t("btn_new_message_title", lang)},
                {"id": "btn_cancel", "title": t("btn_cancel_title", lang)},
            ],
        )


async def handle_text_message(sender: str, name: str, text: str) -> None:
    """Verarbeitet eine eingehende Textnachricht."""
    print(f"[BOT] Textnachricht: '{text}'")
    lang = detect_lang(sender)

    state = user_state.get(sender)

    # --- State vorhanden → Freitext je nach Step verarbeiten ---
    if state:
        step = state.get("step")

        if step == "awaiting_phone":
            await _process_phone_number(sender, text)
            return

        if step == "awaiting_message":
            await _process_message_text(sender, text)
            return

        if step == "confirm_message":
            # Unerwarteter Freitext — Bestaetigungs-Buttons erneut senden
            await send_interactive_buttons(
                sender,
                t("choose_option", lang),
                [
                    {"id": "btn_send", "title": t("btn_send_title", lang)},
                    {"id": "btn_new_message", "title": t("btn_new_message_title", lang)},
                    {"id": "btn_cancel", "title": t("btn_cancel_title", lang)},
                ],
            )
            return

    # --- Kein State → vCard/Radicale + Willkommensmenue ---
    print(f"[STUB] vCard fuer {sender} ({name}) wuerde hier erstellt.")
    await create_vcard(phone_number=sender, display_name=name)
    print(f"[STUB] Radicale-Sync fuer {sender} wuerde hier laufen.")
    await sync_contact(phone_number=sender, display_name=name)

    await send_welcome_menu(sender)


async def handle_button_reply(sender: str, name: str, button_id: str) -> None:
    """Verarbeitet einen Button-Klick."""
    print(f"[BOT] Button-Klick: {button_id}")
    lang = detect_lang(sender)

    if button_id == "btn_callback":
        await send_interactive_buttons(
            sender,
            t("ask_callback_number", lang, phone=sender),
            [
                {"id": "btn_confirm_number", "title": t("btn_confirm_number_title", lang)},
                {"id": "btn_other_number", "title": t("btn_other_number_title", lang)},
                {"id": "btn_cancel", "title": t("btn_cancel_title", lang)},
            ],
        )

    elif button_id == "btn_confirm_number":
        print(f"[STUB] Rueckruf bestaetigt — SMS/Benachrichtigung ausgeloest.")
        user_state.pop(sender, None)
        await send_interactive_buttons(
            sender,
            t("callback_confirmed", lang),
            [
                {"id": "btn_more", "title": t("btn_more_title", lang)},
                {"id": "btn_end", "title": t("btn_end_title", lang)},
            ],
        )

    elif button_id == "btn_other_number":
        user_state[sender] = {"step": "awaiting_phone"}
        await send_text(sender, t("enter_phone", lang))

    elif button_id == "btn_message":
        await send_interactive_buttons(
            sender,
            t("choose_channel", lang),
            [
                {"id": "btn_channel_sms", "title": t("btn_sms_title", lang)},
                {"id": "btn_channel_email", "title": t("btn_email_title", lang)},
                {"id": "btn_cancel", "title": t("btn_cancel_title", lang)},
            ],
        )

    elif button_id == "btn_channel_sms":
        user_state[sender] = {"step": "awaiting_message", "channel": "sms"}
        channel_label = t("label_sms", lang)
        await send_text(sender, t("enter_message", lang, channel=channel_label))

    elif button_id == "btn_channel_email":
        user_state[sender] = {"step": "awaiting_message", "channel": "email"}
        channel_label = t("label_email", lang)
        await send_text(sender, t("enter_message", lang, channel=channel_label))

    elif button_id == "btn_new_message":
        state = user_state.get(sender, {})
        channel = state.get("channel", "sms")
        user_state[sender] = {"step": "awaiting_message", "channel": channel}
        label = t("label_sms", lang) if channel == "sms" else t("label_email", lang)
        await send_text(sender, t("reenter_message", lang, channel=label))

    elif button_id == "btn_send":
        state = user_state.get(sender, {})
        msg_text = state.get("text", "")
        channel = state.get("channel", "unbekannt")
        print(f"[STUB] Nachricht per {channel} versendet: {msg_text}")
        await _send_completion(sender)

    elif button_id == "btn_send_without_attachment":
        state = user_state.get(sender, {})
        msg_text = state.get("text", "")
        channel = state.get("channel", "unbekannt")
        if msg_text:
            print(f"[STUB] Nachricht ohne Anhang per {channel} versendet: {msg_text}")
            await _send_completion(sender)
        else:
            print(f"[STUB] Kein Nachrichtentext im State — Abschluss ohne Versand.")
            user_state.pop(sender, None)
            await send_text(sender, t("no_message_to_send", lang))
            await send_welcome_menu(sender)

    elif button_id == "btn_more":
        user_state.pop(sender, None)
        await send_welcome_menu(sender)

    elif button_id == "btn_end":
        user_state.pop(sender, None)
        await send_text(sender, t("goodbye", lang))

    elif button_id == "btn_cancel":
        user_state.pop(sender, None)
        await send_text(sender, t("goodbye_cancel", lang))

    else:
        print(f"[BOT] Unbekannter Button: {button_id}")
        await send_welcome_menu(sender)


async def handle_list_reply(sender: str, name: str, list_id: str) -> None:
    """Verarbeitet eine Auswahl aus einer List Message."""
    print(f"[BOT] List-Auswahl: {list_id}")
    lang = detect_lang(sender)
    await send_text(sender, t("list_selection", lang, selection=list_id))


async def handle_attachment(sender: str, media_type: str, caption: str | None = None) -> None:
    """Reagiert auf Medien-Anhaenge."""
    print(f"[BOT] Anhang erhalten: {media_type}, Caption: {caption!r}")
    lang = detect_lang(sender)

    state = user_state.get(sender)

    if state and state.get("step") == "awaiting_message":
        if caption:
            # Caption vorhanden — bei SMS erst validieren
            channel = state["channel"]
            if channel == "sms":
                errors = _validate_sms(caption, lang)
                if errors:
                    msg = "\n".join(errors)
                    await send_interactive_buttons(
                        sender,
                        t("attachment_validation_failed", lang, errors=msg),
                        [
                            {"id": "btn_new_message", "title": t("btn_new_message_title", lang)},
                            {"id": "btn_cancel", "title": t("btn_cancel_title", lang)},
                        ],
                    )
                    return

            # Validierung bestanden (oder Email) — State speichern
            user_state[sender] = {
                "step": "confirm_message",
                "channel": channel,
                "text": caption,
            }
            await send_interactive_buttons(
                sender,
                t("attachment_send_without", lang, text=caption),
                [
                    {"id": "btn_send_without_attachment", "title": t("btn_without_attachment_title", lang)},
                    {"id": "btn_new_message", "title": t("btn_new_message_title", lang)},
                    {"id": "btn_cancel", "title": t("btn_cancel_title", lang)},
                ],
            )
        else:
            # Kein Text dabei — nur Hinweis, Text einzugeben
            await send_interactive_buttons(
                sender,
                t("attachment_enter_text", lang),
                [
                    {"id": "btn_new_message", "title": t("btn_new_message_title", lang)},
                    {"id": "btn_cancel", "title": t("btn_cancel_title", lang)},
                ],
            )
    else:
        # Kein aktiver Flow — Hinweis + zurueck zum Menue
        await send_text(sender, t("attachment_not_supported", lang))
        await send_welcome_menu(sender)


async def send_welcome_menu(sender: str) -> None:
    """Sendet das Hauptmenu mit den drei Optionen."""
    lang = detect_lang(sender)
    body = t("welcome_body", lang, mobile=CONTACT_MOBILE, landline=CONTACT_LANDLINE, email=CONTACT_EMAIL)
    buttons = [
        {"id": "btn_callback", "title": t("btn_callback_title", lang)},
        {"id": "btn_message", "title": t("btn_message_title", lang)},
        {"id": "btn_cancel", "title": t("btn_cancel_title", lang)},
    ]
    await send_interactive_buttons(sender, body, buttons)
