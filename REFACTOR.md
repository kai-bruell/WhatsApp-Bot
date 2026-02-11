Ich möchte nun den Punkt '- [ ] Chat-Flow Nachrichten nach Praeferenzen anpassen' aus @TODO.md fertig stellen.

Hier meine Konkreten Anforderungen dafür

Gerade beginnt der Chat folgendermaßen:

```
Bevor wir fortfahren: Duerfen wir Ihre Kontaktdaten speichern...
```

Ich würde es aber folgendermaßen machen:

Als erstes kommt die Begrüßungsnachrricht:

```
Hallo, ich bin persoenlich nicht auf WhatsApp erreichbar.

    📱 Mobil (SMS): {mobile}
    ☎️ Festnetz: {landline}
    📧 Email: {email}

Möchten Sie mir direkt hier eine Nachricht hinterlassen?

Damit ich Ihre Daten (Name, Telefon, E-Mail) speichern und Ihre Anfrage bearbeiten darf, bestätigen Sie bitte kurz meine AGB und Datenschutzbestimmungen. Im Anschluss schaltet sich das Nachrichtenfeld für Sie frei.

<BASE_URL>/privacy
<BASE_URL>/terms

[Akzeptieren]
[Nicht Speichern]
```

