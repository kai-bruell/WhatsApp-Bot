Konkret heißt das: Meta stellt dir nur die **UI-Komponenten** (Buttons, Listen, Menüs) zur Verfügung, aber du musst die **Event-Handler** in deinem Python-Code selbst schreiben.

Wenn ein User auf einen Button klickt, schickt Meta einen Webhook-POST an dich, der keine Nachricht (`text`), sondern ein `button_payload` enthält.

### 1. Interaktive Elemente (Was geht?)

Es gibt drei Haupt-Elemente, die du nutzen kannst, um die KI-Interaktion zu steuern:

| Element | Nutzen | Limit |
| --- | --- | --- |
| **Quick Replies** | Bis zu 3 Buttons unter einer Nachricht. | 20 Zeichen pro Button |
| **List Messages** | Ein Menü, das sich öffnet (z.B. "Wähle ein Thema"). | Bis zu 10 Einträge |
| **CTA URL Buttons** | Buttons, die eine Website öffnen. | Nur in Templates (außerhalb 24h) |

---

### 2. Beispiel: Die "KI-Wahl" (Code-Logik)

Wenn du willst, dass der User per Button entscheidet, ob er mit der KI reden oder ein Ticket eröffnen will, sendest du diesen Payload:

```python
async def send_interactive_buttons(to):
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": "Wie kann ich dir helfen?"},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": "btn_ai", "title": "KI Fragen"}},
                    {"type": "reply", "reply": {"id": "btn_ticket", "title": "Ticket erstellen"}}
                ]
            }
        }
    }
    # ... Standard POST an Meta URL

```

### 3. Was du im Webhook empfängst

Klickt der User auf "KI Fragen", schickt Meta dir ein JSON, das du in deinem `webhook`-Endpunkt abfangen musst:

```python
# In deinem POST-Handler
if 'interactive' in val['messages'][0]:
    button_id = val['messages'][0]['interactive']['button_reply']['id']
    if button_id == "btn_ai":
        # Starte KI-Modus

```

---

### 4. Das AGB-Problem beim Bot

Meta schreibt vor, dass ein automatisierter Bot immer eine **Eskalationsmöglichkeit zu einem echten Menschen** haben muss.

* Du darfst den User nicht in einer KI-Endlosschleife einsperren.
* Ein Befehl wie "Hilfe" oder ein Menüpunkt "Mitarbeiter sprechen" ist Pflicht, wenn du die App offiziell verifizieren willst.

### 5. Außerhalb der 24h

Hier kannst du keine interaktiven Nachrichten "einfach so" schicken. Du musst im Meta Business Manager ein **Template** erstellen, das Buttons enthält, und dieses von Meta absegnen lassen. Erst wenn es den Status `Approved` hat, darfst du es nach Ablauf der 24h senden.

