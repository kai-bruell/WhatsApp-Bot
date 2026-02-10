Diese Dokumentation beschreibt die technische Umsetzung einer selbst gehosteten Kontakt-Synchronisation zwischen deinem WhatsApp-Bot und deinen Mobilgeräten (Android/iOS) unter Verwendung von **Radicale**.

### 1. Architektur-Übersicht

Der Radicale-Server dient als zentrale Instanz ("Single Source of Truth"). Er verwaltet Kontakte als `.vcf`-Dateien (vCards) im Dateisystem.

* **Bot:** Agiert als Client und lädt bei neuen WhatsApp-Kontakten vCards via HTTP-PUT hoch.
* **Mobilgeräte:** Synchronisieren sich bidirektional via CardDAV mit dem Server. Änderungen am Handy werden auf den Server zurückgeschrieben und sind für den Bot lesbar.

---

### 2. Server-Setup (Radicale)

Radicale ist ein leichtgewichtiger, in Python geschriebener CalDAV- und CardDAV-Server.

**Installation via Docker (Empfohlen):**

```yaml
# docker-compose.yml
services:
  radicale:
    image: tomsandro/radicale
    container_name: radicale
    ports:
      - "5232:5232"
    volumes:
      - ./data:/data
    restart: unless-stopped

```

**Sicherheits-Konfiguration (`config`):**
Du solltest die Authentifizierung aktivieren, um unbefugten Zugriff zu verhindern:

```ini
[auth]
type = htpasswd
htpasswd_filename = /data/users
htpasswd_encryption = bcrypt

```

---

### 3. Bot-Implementierung (Python)

Dein Bot nutzt das vCard 3.0 Format, um Kontakte standardkonform zu speichern. Die Synchronisation erfolgt über einfache HTTP-Requests an die Radicale-API.

**Beispiel: Neuen Kontakt anlegen**

```python
import httpx

async def sync_to_radicale(phone_number, name):
    # vCard 3.0 String generieren
    vcard = f"""BEGIN:VCARD
VERSION:3.0
FN:{name}
TEL;TYPE=CELL:{phone_number}
END:VCARD"""

    # URL-Struktur: http://server:5232/user/adressbuch/dateiname.vcf
    url = f"http://localhost:5232/dein_user/contacts/{phone_number}.vcf"
    auth = ("bot_user", "passwort")

    async with httpx.AsyncClient() as client:
        # PUT erstellt die Datei oder überschreibt sie (Update)
        response = await client.put(url, content=vcard, auth=auth)
        return response.status_code in [201, 204]

```

---

### 4. Client-Synchronisation (Handy)

Damit die vom Bot erstellten Kontakte auf deinem Telefon erscheinen, musst du den CardDAV-Account einmalig einrichten.

* **iOS (Nativ):** In den Einstellungen unter *Kontakte > Accounts > Account hinzufügen > Andere > CardDAV-Account* die Server-URL und Zugangsdaten hinterlegen.
* **Android (DAVx⁵):** Da Android CardDAV nicht nativ unterstützt, wird die Open-Source-App **DAVx⁵** benötigt (kostenlos via F-Droid). Diese verknüpft den Radicale-Server mit der systemeigenen Kontakte-App.

---

### 5. Vorteile dieser Lösung

* **Keine Dubletten:** Durch die Benennung der Datei nach der Telefonnummer (z. B. `491701234567.vcf`) wird bei Namensänderungen die bestehende Datei einfach aktualisiert.
* **Offline-Verfügbarkeit:** Die Kontakte werden physisch auf dein Handy synchronisiert und stehen auch ohne Internetverbindung zur Verfügung.
* **Privacy:** Alle Daten bleiben auf deiner eigenen Hardware; kein Sync zu Google- oder Apple-Servern erforderlich.
