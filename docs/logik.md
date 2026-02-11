
---

## Bot-Logik: WhatsApp-to-SMS

### 1. Das Hauptmenü

Startpunkt für jeden neuen Kontakt.

**Begrüßung:**

> Hallo, ich bin persönlich nicht auf WhatsApp erreichbar.
> 📱 **Mobil (SMS):** 123456789
> ☎️ **Festnetz:** 0011223344
> 📧 **Email:** Assistenz@meine-mail.com
> **Was möchten Sie tun?**
> 1️⃣ Um Rückruf bitten
> 2️⃣ Nachricht hinterlassen
> 3️⃣ Abbrechen

---

### 2. Datenerfassung & Abbruch-Option

In jedem Untermenü gibt es den Button **[❌ Abbrechen]**.

* **Rückruf:** Bestätigung der `{WA-Nummer}` oder Eingabe einer neuen Nummer.
* **Nachricht:** Wahl des Rückkanals (`SMS`, `Anruf`, `E-Mail`) und Erfassung der entsprechenden Daten.

---

### 3. High-Level Error Handling (Der Check)

Sobald der User etwas sendet, greift die folgende Kaskade:

#### SCHRITT A: Der kombinierte Regex-Check

Der Bot prüft den Text gegen alle Regeln gleichzeitig und listet **alle** Fehler gesammelt auf.

**Fehler-Liste (Beispiel):**

> ❌ **Mitteilung konnte nicht zugestellt werden:**
> * **Zeichenlimit überschritten:** Ihr Text ist zu lang für den SMS-Versand.
> * **Illegale Zeichen:** Bitte verwenden Sie nur Standardbuchstaben (keine speziellen Symbole).
> * **Anhänge:** Dateianhänge werden nicht unterstützt.
> 
> 
> `[Neu verfassen]` | `[❌ Abbrechen]`

#### SCHRITT B: Der Anhang-Sonderweg

Wenn der **Regex-Check bestanden** ist (Text ist okay), aber dennoch eine Datei/Bild mitgeschickt wurde:

**Bot-Abfrage:**

> ⚠️ **Achtung:** Dateianhänge werden nicht unterstützt.
> Möchten Sie Ihre Nachricht stattdessen **ohne Anhänge** verschicken?
> `[Ohne Anhang verschicken]` | `[Nachricht neu verfassen]` | `[❌ Abbrechen]`

---

### 4. Validierungs-Regeln (Technisch)

| Fehler-Typ | Regel / Bedingung |
| --- | --- |
| **Illegale Zeichen** | Text enthält Zeichen außerhalb von GSM-7 (falls Limit 160) bzw. Unicode-Vorgaben. |
| **Zu viele Zeichen** | > 160 Zeichen bei GSM-7 oder > 70 Zeichen bei Unicode (Emojis). |
| **Anhänge** | Nachrichtentyp ist ungleich `text` (z.B. `image`, `document`, `sticker`). |

---

### 5. Abschluss & Versand

Nachdem der User den Versand bestätigt (entweder direkt oder nach dem "Ohne Anhang"-Check):

1. **Versand:** Nachricht geht als SMS/E-Mail an dich raus.
2. **Bestätigung:**
> "Vielen Dank. Ihre Nachricht wurde übermittelt. ✓"
> `[Weitere Nachricht]` | `[Chat beenden]`



---

### Hilfreiche Regex für deinen Code

Um das sauber zu trennen, hier die Logik für deine Entwicklung:

* **GSM-7 Check:** `^[\w\s\d\.,!@#\$%\^&\*\(\)-=\+\[\]\{\};:'"<>\?\/\\|~]*$` (Falls dies fehlschlägt, gilt das 70er Limit).
* **Char-Counter:** `message.length` (Dynamisch prüfen, ob es zum Zeichensatz-Limit passt).

