"""
Bot-Logik: Steuert den Gespraechsfluss.

Die eigentliche Geschaeftslogik (vCard, Radicale, SMS-Versand) ist noch
Platzhalter — der Bot antwortet aber bereits mit echten WhatsApp-Nachrichten.
"""

from app.messenger import send_text, send_interactive_buttons
from app.vcard import create_vcard
from app.radicale import sync_contact


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
        await handle_attachment(sender, msg_type)

    else:
        print(f"[BOT] Unbekannter Nachrichtentyp: {msg_type}")


async def handle_text_message(sender: str, name: str, text: str) -> None:
    """Verarbeitet eine eingehende Textnachricht."""
    print(f"[BOT] Textnachricht: '{text}'")

    # PLATZHALTER: vCard + Radicale (laeuft im Hintergrund, User merkt nichts)
    print(f"[STUB] vCard fuer {sender} ({name}) wuerde hier erstellt.")
    await create_vcard(phone_number=sender, display_name=name)
    print(f"[STUB] Radicale-Sync fuer {sender} wuerde hier laufen.")
    await sync_contact(phone_number=sender, display_name=name)

    # Echte Antwort: Hauptmenu senden
    await send_welcome_menu(sender)


async def handle_button_reply(sender: str, name: str, button_id: str) -> None:
    """Verarbeitet einen Button-Klick."""
    print(f"[BOT] Button-Klick: {button_id}")

    if button_id == "btn_callback":
        print(f"[STUB] Rueckruf-Flow: Hier wuerde die Nummer validiert und SMS ausgeloest.")
        await send_interactive_buttons(
            sender,
            f"Sollen wir Sie unter Ihrer WhatsApp-Nummer zurueckrufen?",
            [
                {"id": "btn_confirm_number", "title": "Ja, bitte"},
                {"id": "btn_other_number", "title": "Andere Nummer"},
                {"id": "btn_cancel", "title": "Abbrechen"},
            ],
        )

    elif button_id == "btn_confirm_number":
        print(f"[STUB] Rueckruf bestaetigt — hier wuerde SMS/Benachrichtigung ausgeloest.")
        await send_text(
            sender,
            "Vielen Dank. Sie werden so bald wie moeglich zurueckgerufen. \u2713",
        )

    elif button_id == "btn_other_number":
        print(f"[STUB] User will andere Nummer angeben — State wechselt zu AWAITING_NUMBER.")
        await send_text(
            sender,
            "Bitte geben Sie die Rufnummer ein, unter der Sie erreichbar sind:",
        )

    elif button_id == "btn_message":
        print(f"[STUB] Nachrichten-Flow: Hier wuerde der Rueckkanal abgefragt.")
        await send_interactive_buttons(
            sender,
            "Wie moechten Sie kontaktiert werden?",
            [
                {"id": "btn_channel_sms", "title": "SMS"},
                {"id": "btn_channel_email", "title": "E-Mail"},
                {"id": "btn_cancel", "title": "Abbrechen"},
            ],
        )

    elif button_id in ("btn_channel_sms", "btn_channel_email"):
        channel = "SMS" if button_id == "btn_channel_sms" else "E-Mail"
        print(f"[STUB] Kanal gewaehlt: {channel} — State wechselt zu AWAITING_MESSAGE.")
        await send_text(
            sender,
            f"Bitte geben Sie Ihre Nachricht ein (Rueckkanal: {channel}):",
        )

    elif button_id == "btn_cancel":
        await send_text(sender, "Chat beendet. Auf Wiedersehen!")

    elif button_id == "btn_send_without_attachment":
        print(f"[STUB] Nachricht ohne Anhang — hier wuerde SMS/Email versendet.")
        await send_text(sender, "Vielen Dank. Ihre Nachricht wurde uebermittelt. \u2713")

    else:
        print(f"[BOT] Unbekannter Button: {button_id}")
        await send_welcome_menu(sender)


async def handle_list_reply(sender: str, name: str, list_id: str) -> None:
    """Verarbeitet eine Auswahl aus einer List Message."""
    print(f"[BOT] List-Auswahl: {list_id}")
    await send_text(sender, f"Auswahl '{list_id}' erhalten.")


async def handle_attachment(sender: str, media_type: str) -> None:
    """Reagiert auf Medien-Anhaenge."""
    print(f"[BOT] Anhang erhalten: {media_type}")
    print(f"[STUB] Validierung: Anhaenge werden nicht unterstuetzt.")
    await send_interactive_buttons(
        sender,
        "Dateianhange werden leider nicht unterstuetzt.\n"
        "Moechten Sie Ihre Nachricht ohne Anhang verschicken?",
        [
            {"id": "btn_send_without_attachment", "title": "Ohne Anhang senden"},
            {"id": "btn_cancel", "title": "Abbrechen"},
        ],
    )


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
