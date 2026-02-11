"""
Bot-Logik: Steuert den Gespraechsfluss.

Die eigentliche Geschaeftslogik (vCard, Radicale, SMS-Versand) ist noch
Platzhalter — der Bot antwortet aber bereits mit echten WhatsApp-Nachrichten.
"""

import re

from app.messenger import send_text, send_interactive_buttons
from app.vcard import create_vcard
from app.radicale import sync_contact

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

def _validate_sms(text: str) -> list[str]:
    """Prueft GSM-7-Kompatibilitaet und Zeichenlimit. Gibt Fehlerliste zurueck."""
    errors: list[str] = []
    gsm7_pattern = re.compile(
        r"^[\w\s\d.,!@#$%^&*()\-=+\[\]{};:'\"<>?/\\|~\n\r]*$"
    )
    is_gsm7 = bool(gsm7_pattern.match(text))
    limit = 160 if is_gsm7 else 70

    if not is_gsm7:
        errors.append(
            "**Illegale Zeichen:** Bitte verwenden Sie nur Standardbuchstaben."
        )
    if len(text) > limit:
        errors.append(
            f"**Zeichenlimit ueberschritten:** Ihr Text hat {len(text)} Zeichen (max. {limit})."
        )
    return errors


# ---------------------------------------------------------------------------
# Private Flow-Funktionen
# ---------------------------------------------------------------------------

async def _process_phone_number(sender: str, text: str) -> None:
    """Validiert eine eingegebene Rufnummer."""
    cleaned = text.strip()
    if not _PHONE_RE.match(cleaned):
        await send_text(
            sender,
            "Ungueltige Rufnummer. Bitte erneut eingeben:",
        )
        return  # State bleibt auf awaiting_phone

    # Erfolg
    user_state.pop(sender, None)
    print(f"[STUB] Rueckruf an {cleaned} wird veranlasst.")
    await send_interactive_buttons(
        sender,
        f"Rueckruf an {cleaned} wird veranlasst.",
        [
            {"id": "btn_more", "title": "Weitere Nachricht"},
            {"id": "btn_end", "title": "Chat beenden"},
        ],
    )


async def _process_message_text(sender: str, text: str) -> None:
    """Validiert eine eingegebene Nachricht (SMS/Email)."""
    state = user_state[sender]
    channel = state["channel"]

    if channel == "sms":
        errors = _validate_sms(text)
        if errors:
            msg = "\n".join(errors)
            await send_interactive_buttons(
                sender,
                f"Ihre Nachricht konnte nicht validiert werden:\n\n{msg}",
                [
                    {"id": "btn_new_message", "title": "Neu verfassen"},
                    {"id": "btn_cancel", "title": "Abbrechen"},
                ],
            )
            return  # State bleibt auf awaiting_message

    # Validierung bestanden (oder Email — keine Einschraenkung)
    user_state[sender] = {
        "step": "confirm_message",
        "channel": channel,
        "text": text,
    }
    label = "SMS" if channel == "sms" else "E-Mail"
    await send_interactive_buttons(
        sender,
        f"Ihre Nachricht per {label}:\n\n\"{text}\"\n\nSoll diese Nachricht gesendet werden?",
        [
            {"id": "btn_send", "title": "Senden"},
            {"id": "btn_new_message", "title": "Neu verfassen"},
            {"id": "btn_cancel", "title": "Abbrechen"},
        ],
    )


async def _send_completion(sender: str) -> None:
    """Sendet den Abschluss-Flow und loescht den State."""
    user_state.pop(sender, None)
    await send_interactive_buttons(
        sender,
        "Vielen Dank. Ihre Nachricht wurde uebermittelt. \u2713",
        [
            {"id": "btn_more", "title": "Weitere Nachricht"},
            {"id": "btn_end", "title": "Chat beenden"},
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
            "Dieser Nachrichtentyp wird leider nicht unterstuetzt.\n"
            "Bitte geben Sie Ihre Nachricht als Text ein.",
            [
                {"id": "btn_new_message", "title": "Neu verfassen"},
                {"id": "btn_cancel", "title": "Abbrechen"},
            ],
        )


async def handle_text_message(sender: str, name: str, text: str) -> None:
    """Verarbeitet eine eingehende Textnachricht."""
    print(f"[BOT] Textnachricht: '{text}'")

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
                "Bitte waehlen Sie eine der Optionen:",
                [
                    {"id": "btn_send", "title": "Senden"},
                    {"id": "btn_new_message", "title": "Neu verfassen"},
                    {"id": "btn_cancel", "title": "Abbrechen"},
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

    if button_id == "btn_callback":
        await send_interactive_buttons(
            sender,
            "Sollen wir Sie unter Ihrer WhatsApp-Nummer zurueckrufen?",
            [
                {"id": "btn_confirm_number", "title": "Ja, bitte"},
                {"id": "btn_other_number", "title": "Andere Nummer"},
                {"id": "btn_cancel", "title": "Abbrechen"},
            ],
        )

    elif button_id == "btn_confirm_number":
        print(f"[STUB] Rueckruf bestaetigt — SMS/Benachrichtigung ausgeloest.")
        user_state.pop(sender, None)
        await send_interactive_buttons(
            sender,
            "Vielen Dank. Sie werden so bald wie moeglich zurueckgerufen.",
            [
                {"id": "btn_more", "title": "Weitere Nachricht"},
                {"id": "btn_end", "title": "Chat beenden"},
            ],
        )

    elif button_id == "btn_other_number":
        user_state[sender] = {"step": "awaiting_phone"}
        await send_text(
            sender,
            "Bitte geben Sie die Rufnummer ein, unter der Sie erreichbar sind:",
        )

    elif button_id == "btn_message":
        await send_interactive_buttons(
            sender,
            "Wie moechten Sie kontaktiert werden?",
            [
                {"id": "btn_channel_sms", "title": "SMS"},
                {"id": "btn_channel_email", "title": "E-Mail"},
                {"id": "btn_cancel", "title": "Abbrechen"},
            ],
        )

    elif button_id == "btn_channel_sms":
        user_state[sender] = {"step": "awaiting_message", "channel": "sms"}
        await send_text(
            sender,
            "Bitte geben Sie Ihre Nachricht ein (Rueckkanal: SMS):",
        )

    elif button_id == "btn_channel_email":
        user_state[sender] = {"step": "awaiting_message", "channel": "email"}
        await send_text(
            sender,
            "Bitte geben Sie Ihre Nachricht ein (Rueckkanal: E-Mail):",
        )

    elif button_id == "btn_new_message":
        state = user_state.get(sender, {})
        channel = state.get("channel", "sms")
        user_state[sender] = {"step": "awaiting_message", "channel": channel}
        label = "SMS" if channel == "sms" else "E-Mail"
        await send_text(
            sender,
            f"Bitte geben Sie Ihre Nachricht neu ein (Rueckkanal: {label}):",
        )

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
            await send_text(sender, "Es liegt keine Nachricht zum Senden vor.")
            await send_welcome_menu(sender)

    elif button_id == "btn_more":
        user_state.pop(sender, None)
        await send_welcome_menu(sender)

    elif button_id == "btn_end":
        user_state.pop(sender, None)
        await send_text(sender, "Auf Wiedersehen!")

    elif button_id == "btn_cancel":
        user_state.pop(sender, None)
        await send_text(sender, "Chat beendet. Auf Wiedersehen!")

    else:
        print(f"[BOT] Unbekannter Button: {button_id}")
        await send_welcome_menu(sender)


async def handle_list_reply(sender: str, name: str, list_id: str) -> None:
    """Verarbeitet eine Auswahl aus einer List Message."""
    print(f"[BOT] List-Auswahl: {list_id}")
    await send_text(sender, f"Auswahl '{list_id}' erhalten.")


async def handle_attachment(sender: str, media_type: str, caption: str | None = None) -> None:
    """Reagiert auf Medien-Anhaenge."""
    print(f"[BOT] Anhang erhalten: {media_type}, Caption: {caption!r}")

    state = user_state.get(sender)

    if state and state.get("step") == "awaiting_message":
        if caption:
            # Caption vorhanden — bei SMS erst validieren
            channel = state["channel"]
            if channel == "sms":
                errors = _validate_sms(caption)
                if errors:
                    msg = "\n".join(errors)
                    await send_interactive_buttons(
                        sender,
                        f"Anhaenge werden nicht unterstuetzt und der Text "
                        f"konnte nicht validiert werden:\n\n{msg}",
                        [
                            {"id": "btn_new_message", "title": "Neu verfassen"},
                            {"id": "btn_cancel", "title": "Abbrechen"},
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
                "Anhaenge werden leider nicht unterstuetzt.\n"
                "Moechten Sie Ihre Nachricht ohne Anhang senden?\n\n"
                f"Ihr Text:\n\"{caption}\"",
                [
                    {"id": "btn_send_without_attachment", "title": "Ohne Anhang"},
                    {"id": "btn_new_message", "title": "Neu verfassen"},
                    {"id": "btn_cancel", "title": "Abbrechen"},
                ],
            )
        else:
            # Kein Text dabei — nur Hinweis, Text einzugeben
            await send_interactive_buttons(
                sender,
                "Anhaenge werden leider nicht unterstuetzt.\n"
                "Bitte geben Sie Ihre Nachricht als Text ein.",
                [
                    {"id": "btn_new_message", "title": "Neu verfassen"},
                    {"id": "btn_cancel", "title": "Abbrechen"},
                ],
            )
    else:
        # Kein aktiver Flow — Hinweis + zurueck zum Menue
        await send_text(
            sender,
            "Dateianhange werden leider nicht unterstuetzt.",
        )
        await send_welcome_menu(sender)


async def send_welcome_menu(sender: str) -> None:
    """Sendet das Hauptmenu mit den drei Optionen."""
    body = (
        "Hallo, ich bin persoenlich nicht auf WhatsApp erreichbar.\n\n"
        "\U0001f4f1 Mobil (SMS): 123456789\n"
        "\u260e\ufe0f Festnetz: 0011223344\n"
        "\U0001f4e7 Email: Assistenz@meine-mail.com\n\n"
        "Was moechten Sie tun?"
    )
    buttons = [
        {"id": "btn_callback", "title": "Rueckruf erbitten"},
        {"id": "btn_message", "title": "Nachricht senden"},
        {"id": "btn_cancel", "title": "Abbrechen"},
    ]
    await send_interactive_buttons(sender, body, buttons)
