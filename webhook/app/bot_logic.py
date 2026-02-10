"""
Bot-Logik: Steuert den Gespraechsfluss (State Machine).

Jeder Schritt beschreibt per Platzhalter-Antwort, welche Aktion
an dieser Stelle spaeter ausgefuehrt wird.
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

    # PLATZHALTER: Hier wuerde die Conversation-State-Machine greifen.
    # Je nach aktuellem State des Users (z.B. MENU, AWAITING_CALLBACK_NUMBER,
    # AWAITING_MESSAGE) wuerde unterschiedlich reagiert werden.

    # Schritt 1: vCard-Erstellung / Update
    print(f"[SCHRITT] vCard fuer {sender} ({name}) wuerde hier erstellt/aktualisiert.")
    await create_vcard(phone_number=sender, display_name=name)

    # Schritt 2: Radicale-Sync
    print(f"[SCHRITT] Kontakt {sender} wuerde hier mit Radicale synchronisiert.")
    await sync_contact(phone_number=sender, display_name=name)

    # Schritt 3: Begruessungs-Menu senden
    print(f"[SCHRITT] Hauptmenu wuerde hier an {sender} gesendet.")
    await send_welcome_menu(sender)


async def handle_button_reply(sender: str, name: str, button_id: str) -> None:
    """Verarbeitet einen Button-Klick."""
    print(f"[BOT] Button-Klick: {button_id}")

    if button_id == "btn_callback":
        print(f"[SCHRITT] Rueckruf-Flow wuerde hier starten fuer {sender}.")
        print(f"[SCHRITT] User wuerde nach Rufnummer-Bestaetigung gefragt.")
        await send_text(
            sender,
            f"[PLATZHALTER] Rueckruf-Flow: Ihre WhatsApp-Nummer ({sender}) wird als "
            f"Rueckrufnummer verwendet. Bestaetigen oder neue Nummer eingeben."
        )

    elif button_id == "btn_message":
        print(f"[SCHRITT] Nachrichten-Flow wuerde hier starten fuer {sender}.")
        print(f"[SCHRITT] User wuerde nach Rueckkanal gefragt (SMS/Anruf/Email).")
        await send_text(
            sender,
            "[PLATZHALTER] Nachrichten-Flow: Bitte waehlen Sie den Rueckkanal "
            "(SMS, Anruf oder E-Mail)."
        )

    elif button_id == "btn_cancel":
        print(f"[SCHRITT] Abbruch durch User {sender}.")
        await send_text(sender, "[PLATZHALTER] Chat wurde beendet. Auf Wiedersehen!")

    else:
        print(f"[BOT] Unbekannter Button: {button_id}")


async def handle_list_reply(sender: str, name: str, list_id: str) -> None:
    """Verarbeitet eine Auswahl aus einer List Message."""
    print(f"[BOT] List-Auswahl: {list_id}")
    print(f"[SCHRITT] Aktion fuer List-ID '{list_id}' wuerde hier ausgefuehrt.")
    await send_text(sender, f"[PLATZHALTER] List-Auswahl '{list_id}' erhalten.")


async def handle_attachment(sender: str, media_type: str) -> None:
    """Reagiert auf Medien-Anhaenge (Bilder, Dokumente etc.)."""
    print(f"[BOT] Anhang erhalten: {media_type}")
    print(f"[SCHRITT] Validierung: Anhaenge werden nicht unterstuetzt.")
    print(f"[SCHRITT] User wuerde gefragt, ob Nachricht ohne Anhang gesendet werden soll.")
    await send_text(
        sender,
        "[PLATZHALTER] Dateianhange werden nicht unterstuetzt. "
        "Moechten Sie Ihre Nachricht stattdessen ohne Anhang verschicken?"
    )


async def send_welcome_menu(sender: str) -> None:
    """Sendet das Hauptmenu mit den drei Optionen."""
    print(f"[SCHRITT] Begruessungs-Menu wird an {sender} gesendet.")

    body = (
        "Hallo, ich bin persoenlich nicht auf WhatsApp erreichbar.\n"
        "Was moechten Sie tun?"
    )
    buttons = [
        {"id": "btn_callback", "title": "Um Rueckruf bitten"},
        {"id": "btn_message", "title": "Nachricht senden"},
        {"id": "btn_cancel", "title": "Abbrechen"},
    ]
    await send_interactive_buttons(sender, body, buttons)
