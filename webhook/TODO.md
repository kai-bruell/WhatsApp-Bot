## TODO: Chat perfektionieren

### 1. waiting_for Dict
- Minimales In-Memory Dict in `bot_logic.py`
- Speichert pro User ob Freitext erwartet wird: `"message"` oder `"phone_number"`
- Key vorhanden → Freitext verarbeiten, Key nicht vorhanden → Willkommensmenu

### 2. Regex-Validierung (logik.md)
- GSM-7 Check bei eingehender Nachricht
- Zeichenlimit: 160 (GSM-7) / 70 (Unicode/Emojis)
- Alle Fehler gesammelt anzeigen
- Buttons: [Neu verfassen] | [Abbrechen]
- Check bestanden → Bestaetigung mit [Senden] | [Abbrechen]

### 3. Anhang-Sonderweg
- Anhang im Nachrichten-Flow → "Ohne Anhang senden?" mit Buttons
- Anhang ausserhalb des Flows → Hinweis + zurueck zum Menu

### 4. Rufnummer-Validierung
- Plausibilitaets-Check wenn User alternative Nummer eingibt
- Fehler → "Ungueltige Nummer, bitte erneut eingeben"
- Erfolg → Rueckruf-Bestaetigung

### 5. Abschluss-Flow
- Nach Versand: "Vielen Dank. Ihre Nachricht wurde uebermittelt. ✓"
- Buttons: [Weitere Nachricht] | [Chat beenden]
- waiting_for Key loeschen

---
> Siehe `logik.md` fuer die vollstaendige Spezifikation der Bot-Logik.
