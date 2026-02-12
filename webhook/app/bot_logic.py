"""
Bot-Logik: Steuert den Gespraechsfluss.

Die eigentliche Geschaeftslogik (vCard, Radicale, SMS-Versand) ist noch
Platzhalter — der Bot antwortet aber bereits mit echten WhatsApp-Nachrichten.
"""

import re
from collections import deque

from app.messenger import send_text, send_interactive_buttons
from app.vcard import create_vcard
from app.radicale import sync_contact
from app.i18n import t, detect_lang
from app.config import (
    CONTACT_MOBILE, CONTACT_LANDLINE, CONTACT_EMAIL,
    PRIVACY_URL, TERMS_URL, MAX_CALLBACKS_DAY,
)
from app.rate_limit import limiter
from app.consent import consent_store
from app.data_deletion import purge_by_phone, register_state_cleanup

# ---------------------------------------------------------------------------
# User-State: trackt pro Sender, in welchem Schritt er sich befindet.
# ---------------------------------------------------------------------------
user_state: dict[str, dict] = {}

# Circular-Import-freie Anbindung: data_deletion.purge_by_phone raeumt State auf
register_state_cleanup(lambda phone: user_state.pop(phone, None))

_PHONE_RE = re.compile(r"^\+?\d[\d\s\-/]{6,18}\d$")
_POLICY_KEYWORDS = {"policy", "datenschutz", "privacy", "agb", "terms", "tos"}
_seen_msg_ids: deque[str] = deque(maxlen=1000)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _buttons(sender: str, msg_key: str, btn_ids: list[str], **fmt) -> None:
    """Sendet Nachricht mit Buttons (Titel-Key per Konvention: {btn_id}_title)."""
    lang = detect_lang(sender)
    await send_interactive_buttons(
        sender,
        t(msg_key, lang, **fmt),
        [{"id": b, "title": t(f"{b}_title", lang)} for b in btn_ids],
    )


def _format_wait(seconds: int, lang: str) -> str:
    if seconds >= 3600:
        return t("wait_hours", lang, count=seconds // 3600)
    if seconds >= 60:
        return t("wait_minutes", lang, count=seconds // 60)
    return t("wait_seconds", lang, count=seconds)


async def _check_channel_limit(sender: str, channel: str, lang: str) -> bool:
    """Prueft Rate-Limit fuer SMS/Email. Gibt True zurueck falls blockiert."""
    if channel == "sms":
        result = limiter.check_sms(sender)
    elif channel == "email":
        result = limiter.check_email(sender)
    else:
        return False
    if result:
        err_key, wait = result
        user_state.pop(sender, None)
        await send_text(sender, t(err_key, lang, wait=_format_wait(wait, lang)))
        await send_welcome_menu(sender)
        return True
    return False


def _validate_sms(text: str, lang: str) -> list[str]:
    errors: list[str] = []
    gsm7 = bool(re.match(r"^[\w\s\d.,!@#$%^&*()\-=+\[\]{};:'\"<>?/\\|~\n\r]*$", text))
    limit = 160 if gsm7 else 70
    if not gsm7:
        errors.append(t("illegal_chars", lang))
    if len(text) > limit:
        errors.append(t("char_limit_exceeded", lang, count=len(text), limit=limit))
    return errors


# ---------------------------------------------------------------------------
# Private Flow-Funktionen
# ---------------------------------------------------------------------------

async def _ask_consent(sender: str) -> None:
    await _buttons(sender, "consent_ask", ["btn_consent_yes", "btn_consent_no"],
                   mobile=CONTACT_MOBILE, landline=CONTACT_LANDLINE, email=CONTACT_EMAIL,
                   privacy_url=PRIVACY_URL, terms_url=TERMS_URL)


async def _show_policy_menu(sender: str) -> None:
    lang = detect_lang(sender)
    buttons: list[dict] = []
    if consent_store.has_consented(sender):
        buttons.append({"id": "btn_delete_data", "title": t("btn_delete_data_title", lang)})
    buttons.append({"id": "btn_more", "title": t("btn_more_title", lang)})
    buttons.append({"id": "btn_end", "title": t("btn_end_title", lang)})
    await send_interactive_buttons(
        sender, t("policy_menu", lang, privacy_url=PRIVACY_URL, terms_url=TERMS_URL), buttons,
    )


async def _choose_channel(sender: str) -> None:
    """Zeigt die Kanal-Auswahl (SMS/Email)."""
    lang = detect_lang(sender)
    await send_interactive_buttons(
        sender, t("choose_channel", lang),
        [
            {"id": "btn_channel_sms", "title": t("btn_sms_title", lang)},
            {"id": "btn_channel_email", "title": t("btn_email_title", lang)},
            {"id": "btn_cancel", "title": t("btn_cancel_title", lang)},
        ],
    )


async def _process_phone_number(sender: str, text: str) -> None:
    lang = detect_lang(sender)
    cleaned = text.strip()
    if not _PHONE_RE.match(cleaned):
        await send_text(sender, t("invalid_phone", lang))
        return
    user_state.pop(sender, None)
    limiter.record_callback(sender)
    print(f"[STUB] Rueckruf an {cleaned} wird veranlasst.")
    await _buttons(sender, "callback_initiated", ["btn_more", "btn_end"], phone=cleaned)


async def _process_message_text(sender: str, text: str) -> None:
    lang = detect_lang(sender)
    state = user_state[sender]
    channel = state["channel"]
    if channel == "sms":
        errors = _validate_sms(text, lang)
        if errors:
            await _buttons(sender, "validation_failed", ["btn_new_message", "btn_cancel"],
                           errors="\n".join(errors))
            return
    user_state[sender] = {"step": "confirm_message", "channel": channel, "text": text}
    label = t("label_sms", lang) if channel == "sms" else t("label_email", lang)
    await _buttons(sender, "confirm_message", ["btn_send", "btn_new_message", "btn_cancel"],
                   label=label, text=text)


async def _send_completion(sender: str) -> None:
    user_state.pop(sender, None)
    await _buttons(sender, "message_sent", ["btn_more", "btn_end"])


async def _do_send(sender: str) -> None:
    """Gemeinsame Logik fuer btn_send und btn_send_without_attachment."""
    lang = detect_lang(sender)
    state = user_state.get(sender, {})
    msg_text = state.get("text", "")
    channel = state.get("channel", "unbekannt")
    if not msg_text:
        user_state.pop(sender, None)
        await send_text(sender, t("no_message_to_send", lang))
        await send_welcome_menu(sender)
        return
    if await _check_channel_limit(sender, channel, lang):
        return
    if channel == "sms":
        limiter.record_sms(sender)
    elif channel == "email":
        limiter.record_email(sender)
    print(f"[STUB] Nachricht per {channel} versendet: {msg_text}")
    await _send_completion(sender)


# ---------------------------------------------------------------------------
# Button-Handler
# ---------------------------------------------------------------------------

async def _on_callback(sender: str, name: str) -> None:
    lang = detect_lang(sender)
    cb_count = limiter.callback_count(sender)
    if cb_count >= MAX_CALLBACKS_DAY:
        await send_text(sender, t("callback_limit_reached", lang))
        await send_welcome_menu(sender)
        return
    if cb_count == 1:
        await send_interactive_buttons(
            sender, t("callback_already_requested", lang),
            [
                {"id": "btn_other_number", "title": t("btn_change_number_title", lang)},
                {"id": "btn_more", "title": t("btn_no_thanks_title", lang)},
            ],
        )
        return
    await _buttons(sender, "ask_callback_number",
                   ["btn_confirm_number", "btn_other_number", "btn_cancel"], phone=sender)


async def _on_confirm_number(sender: str, name: str) -> None:
    print("[STUB] Rueckruf bestaetigt — SMS/Benachrichtigung ausgeloest.")
    limiter.record_callback(sender)
    user_state.pop(sender, None)
    await _buttons(sender, "callback_confirmed", ["btn_more", "btn_end"])


async def _on_other_number(sender: str, name: str) -> None:
    user_state[sender] = {"step": "awaiting_phone"}
    await send_text(sender, t("enter_phone", detect_lang(sender)))


async def _on_message(sender: str, name: str) -> None:
    await _choose_channel(sender)


async def _on_channel(sender: str, channel: str) -> None:
    lang = detect_lang(sender)
    user_state[sender] = {"step": "awaiting_message", "channel": channel}
    await send_text(sender, t("enter_message", lang, channel=t(f"label_{channel}", lang)))


async def _on_new_message(sender: str, name: str) -> None:
    lang = detect_lang(sender)
    state = user_state.get(sender, {})
    channel = state.get("channel", "sms")
    user_state[sender] = {"step": "awaiting_message", "channel": channel}
    label = t("label_sms", lang) if channel == "sms" else t("label_email", lang)
    await send_text(sender, t("reenter_message", lang, channel=label))


async def _on_send(sender: str, name: str) -> None:
    await _do_send(sender)


async def _on_consent_yes(sender: str, name: str) -> None:
    consent_store.store_consent(sender, True)
    print(f"[CONSENT] {sender} hat zugestimmt — vCard-Sync")
    await create_vcard(phone_number=sender, display_name=name)
    await sync_contact(phone_number=sender, display_name=name)
    await _buttons(sender, "consent_accepted_body", ["btn_callback", "btn_message", "btn_cancel"])


async def _on_consent_no(sender: str, name: str) -> None:
    consent_store.store_consent(sender, False)
    print(f"[CONSENT] {sender} hat abgelehnt — kein Sync")
    await _buttons(sender, "consent_declined_body", ["btn_callback", "btn_message", "btn_cancel"])


async def _on_delete_data(sender: str, name: str) -> None:
    await _buttons(sender, "delete_data_confirm", ["btn_confirm_delete", "btn_cancel"])


async def _on_confirm_delete(sender: str, name: str) -> None:
    await purge_by_phone(sender)
    await send_text(sender, t("delete_data_done", detect_lang(sender)))


async def _on_more(sender: str, name: str) -> None:
    user_state.pop(sender, None)
    if limiter.callback_count(sender) >= MAX_CALLBACKS_DAY:
        await _choose_channel(sender)
    else:
        await send_welcome_menu(sender)


async def _on_end(sender: str, name: str) -> None:
    user_state.pop(sender, None)
    await send_text(sender, t("goodbye", detect_lang(sender)))


async def _on_cancel(sender: str, name: str) -> None:
    user_state.pop(sender, None)
    await send_text(sender, t("goodbye_cancel", detect_lang(sender)))


_BUTTON_HANDLERS = {
    "btn_callback": _on_callback,
    "btn_confirm_number": _on_confirm_number,
    "btn_other_number": _on_other_number,
    "btn_message": _on_message,
    "btn_channel_sms": lambda s, n: _on_channel(s, "sms"),
    "btn_channel_email": lambda s, n: _on_channel(s, "email"),
    "btn_new_message": _on_new_message,
    "btn_send": _on_send,
    "btn_send_without_attachment": _on_send,
    "btn_consent_yes": _on_consent_yes,
    "btn_consent_no": _on_consent_no,
    "btn_delete_data": _on_delete_data,
    "btn_confirm_delete": _on_confirm_delete,
    "btn_more": _on_more,
    "btn_end": _on_end,
    "btn_cancel": _on_cancel,
}


# ---------------------------------------------------------------------------
# Oeffentliche Handler
# ---------------------------------------------------------------------------

async def handle_incoming_message(message: dict, contact_info: dict) -> None:
    """Zentraler Einstiegspunkt fuer jede eingehende Nachricht."""
    msg_id = message.get("id", "")
    if msg_id:
        if msg_id in _seen_msg_ids:
            print(f"[BOT] Duplizierte Nachricht ignoriert: {msg_id}")
            return
        _seen_msg_ids.append(msg_id)

    sender = message.get("from", "unbekannt")
    msg_type = message.get("type", "unknown")
    contact_name = contact_info.get("profile", {}).get("name", "Unbekannt")
    lang = detect_lang(sender)

    api_result = limiter.check_api(sender)
    if api_result:
        err_key, wait_secs = api_result
        await send_text(sender, t(err_key, lang, wait=_format_wait(wait_secs, lang)))
        return
    limiter.record_api(sender)

    print(f"[BOT] Nachricht von {sender} ({contact_name}), Typ: {msg_type}")

    if msg_type == "text":
        await handle_text_message(sender, contact_name, message["text"]["body"])
    elif msg_type == "interactive":
        interactive = message.get("interactive", {})
        if "button_reply" in interactive:
            await handle_button_reply(sender, contact_name, interactive["button_reply"]["id"])
    elif msg_type in ("image", "document", "audio", "video", "sticker"):
        await handle_attachment(sender, msg_type, message.get(msg_type, {}).get("caption"))
    else:
        print(f"[BOT] Unbekannter Nachrichtentyp: {msg_type}")
        await _buttons(sender, "unsupported_type", ["btn_new_message", "btn_cancel"])


async def handle_text_message(sender: str, name: str, text: str) -> None:
    """Verarbeitet eine eingehende Textnachricht."""
    print(f"[BOT] Textnachricht: '{text}'")
    lang = detect_lang(sender)
    state = user_state.get(sender)

    if state:
        step = state.get("step")
        if step == "awaiting_phone":
            await _process_phone_number(sender, text)
            return
        if step == "awaiting_message":
            await _process_message_text(sender, text)
            return
        if step == "confirm_message":
            await _buttons(sender, "choose_option",
                           ["btn_send", "btn_new_message", "btn_cancel"])
            return

    if text.strip().lower() in _POLICY_KEYWORDS:
        await _show_policy_menu(sender)
        return

    if not consent_store.has_record(sender):
        await _ask_consent(sender)
        return

    if consent_store.has_consented(sender):
        print(f"[CONSENT] vCard-Sync fuer {sender} ({name})")
        await create_vcard(phone_number=sender, display_name=name)
        await sync_contact(phone_number=sender, display_name=name)

    await send_welcome_menu(sender)


async def handle_button_reply(sender: str, name: str, button_id: str) -> None:
    """Verarbeitet einen Button-Klick."""
    print(f"[BOT] Button-Klick: {button_id}")
    handler = _BUTTON_HANDLERS.get(button_id)
    if handler:
        await handler(sender, name)
    else:
        print(f"[BOT] Unbekannter Button: {button_id}")
        await send_welcome_menu(sender)


async def handle_attachment(sender: str, media_type: str, caption: str | None = None) -> None:
    """Reagiert auf Medien-Anhaenge."""
    print(f"[BOT] Anhang erhalten: {media_type}, Caption: {caption!r}")
    lang = detect_lang(sender)
    state = user_state.get(sender)

    if state and state.get("step") == "awaiting_message":
        channel = state["channel"]
        if caption:
            if channel == "sms":
                errors = _validate_sms(caption, lang)
                if errors:
                    await _buttons(sender, "attachment_validation_failed",
                                   ["btn_new_message", "btn_cancel"], errors="\n".join(errors))
                    return
            user_state[sender] = {"step": "confirm_message", "channel": channel, "text": caption}
            await send_interactive_buttons(
                sender, t("attachment_send_without", lang, text=caption),
                [
                    {"id": "btn_send_without_attachment", "title": t("btn_without_attachment_title", lang)},
                    {"id": "btn_new_message", "title": t("btn_new_message_title", lang)},
                    {"id": "btn_cancel", "title": t("btn_cancel_title", lang)},
                ],
            )
        else:
            await _buttons(sender, "attachment_enter_text", ["btn_new_message", "btn_cancel"])
    else:
        await send_text(sender, t("attachment_not_supported", lang))
        await send_welcome_menu(sender)


async def send_welcome_menu(sender: str) -> None:
    """Sendet das Hauptmenu mit den verfuegbaren Optionen."""
    lang = detect_lang(sender)
    buttons = []
    if limiter.callback_count(sender) < MAX_CALLBACKS_DAY:
        buttons.append({"id": "btn_callback", "title": t("btn_callback_title", lang)})
    buttons.append({"id": "btn_message", "title": t("btn_message_title", lang)})
    buttons.append({"id": "btn_cancel", "title": t("btn_cancel_title", lang)})
    await send_interactive_buttons(sender, t("welcome_body", lang), buttons)
