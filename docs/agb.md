
### 1. Die 24h-Regel (Service Window)

Innerhalb von 24h nach der letzten Nachricht des Users darfst du **Free-Form Messages** senden (beliebiger Text, JSON, Medien).

* **Wenn die 24h um sind:** Du kannst technisch keine normale Nachricht mehr senden. Die API liefert einen Fehler.
* **Lösung:** Du musst ein **Template** (Vorlage) nutzen. Diese Vorlagen müssen bei Meta eingereicht und vorab genehmigt werden.
* **Kosten:** Free-Form innerhalb 24h ist (oft) kostenlos im Kontingent, Vorlagen kosten pro Nachricht Geld (Business-Initiated Conversation).

### 2. Bot-Befehle: Meta vs. Eigenbau

* **Meta (Cloud API):** Bietet fast keine Logik. Du kannst dort zwar "Quick Replies" oder "List Messages" (Buttons) definieren, aber das sind nur UI-Elemente.
* **Eigenbau (Empfohlen):** Da du eine KI (LLM) nutzen willst, **muss** die Logik bei dir liegen. Die API ist für dich nur die I/O-Schnittstelle.
* **Vorteil Eigenbau:** Du hast die volle Kontrolle über den State und kannst komplexe Workflows (z.B. RAG für deine Dokumentation) abbilden.

### 3. AGB & Compliance

Meta ist allergisch gegen:

* **Spam:** Wenn zu viele User dich blockieren, wird deine Nummer gesperrt.
* **Sensible Daten:** Keine Passwörter oder Gesundheitsdaten über die API.
* **Opt-out:** Du musst dem User theoretisch die Möglichkeit geben, den Chat zu stoppen (z.B. Befehl "Stop").

---

### Strategie für deine KI:

Da du WhatsApp "loswerden" willst, sollte dein Python-Skript Folgendes tun:

1. Eingehende Nachricht empfangen.
2. In deiner DB prüfen: Ist der User innerhalb der 24h?
3. Falls ja: KI-Antwort generieren und per API senden.
4. Falls nein: Eine Vorlage senden (z.B. "Hallo, ich bin dein Bot. Möchtest du den Chat fortfahren?"), damit der User antwortet und das 24h-Fenster wieder öffnet.

