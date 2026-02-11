# Plan: Meta Data Deletion Callback

## Kontext
Meta verlangt eine "Data Deletion Callback URL" fuer Apps auf der Plattform. Wenn ein Nutzer die App ueber Facebook entfernt, sendet Meta einen POST mit `signed_request`. Der Server muss die Signatur validieren, die Loeschung triggern, und eine Status-URL zurueckgeben. Zusaetzlich braucht es eine einfache HTML-Statusseite.

## Neue/geaenderte Dateien

| Datei | Aktion |
|---|---|
| `webhook/app/data_deletion.py` | **NEU** — Signaturvalidierung, SQLite-Store, Datenloeschung |
| `webhook/app/api.py` | **ANGEPASST** — zwei neue Routen + HTML-Helper |
| `webhook/app/config.py` | **ANGEPASST** — `APP_SECRET` hinzufuegen |
| `.env.example` | **ANGEPASST** — `APP_SECRET` Platzhalter |
| `README.md` | **ANGEPASST** — Doku fuer neuen Endpoint + Config-Tabelle |

Keine Aenderungen an: `__init__.py`, `bot_logic.py`, `rate_limit.py`, `Dockerfile`, `docker-compose.yml`, `requirements.txt` (alles stdlib).

## Aenderungen im Detail

### 1. `webhook/app/config.py` — 1 Zeile
Nach `PHONE_NUMBER_ID` hinzufuegen:
```python
APP_SECRET = os.getenv("APP_SECRET", "")
```

### 2. `webhook/app/data_deletion.py` — Neues Modul
Folgt dem Pattern von `rate_limit.py` (Klasse + Singleton).

**`DataDeletionStore`-Klasse:**
- Nutzt dieselbe SQLite-DB (`RATE_LIMIT_DB`)
- Neue Tabelle `data_deletions` (confirmation_code PK, user_id, requested_at, status)
- Methoden: `create(user_id) -> code`, `get_status(code) -> dict|None`, `mark_completed(code)`

**`parse_signed_request(signed_request) -> dict|None`:**
- Split auf `.` → Signatur + Payload
- Base64url-Decode beider Teile
- HMAC-SHA256 mit `APP_SECRET` validieren (`hmac.compare_digest`)
- JSON-Payload parsen und zurueckgeben
- Gibt `None` bei jedem Fehler zurueck

**`purge_user_data(user_id)`:**
- Loggt die Loeschanfrage
- Aktuell: kein Facebook-user_id-zu-Telefonnummer-Mapping vorhanden → Log-only
- Erweiterbar wenn Mapping-Tabelle existiert

### 3. `webhook/app/api.py` — Zwei neue Routen

**`POST /datadeletion`** — Server-to-Server Callback:
- Liest `signed_request` aus Form-Data (`application/x-www-form-urlencoded`)
- Validiert via `parse_signed_request()`
- Erstellt Loeschung in DB, fuehrt `purge_user_data()` aus, markiert als `completed`
- Response: `{"url": "https://.../datadeletion?id=CODE", "confirmation_code": "CODE"}`

**`GET /datadeletion`** — HTML-Statusseite:
- Query-Parameter `?id=CODE`
- Zeigt Confirmation-Code und Status (`completed`) als minimale HTML-Seite
- 404 wenn Code nicht gefunden

**`_status_page_html(title, body)`** — Helper fuer inline-HTML (kein Template-File noetig).

### 4. `.env.example` + `README.md`
- `APP_SECRET=your_facebook_app_secret_here` in `.env.example`
- Neue Zeile in Config-Tabelle + neuer Abschnitt "Data Deletion Callback" in README

## Request-Flow
1. Nutzer entfernt App in Facebook
2. Meta sendet `POST /datadeletion` mit `signed_request=SIG.PAYLOAD`
3. Server validiert HMAC-SHA256, dekodiert Payload, extrahiert `user_id`
4. Loeschung wird in SQLite gespeichert (UUID als Confirmation-Code)
5. Response mit Status-URL an Meta
6. Nutzer/Meta ruft `GET /datadeletion?id=CODE` auf → HTML-Bestaetigung

## Verifizierung
```bash
docker compose up -d --build

# POST-Test (ohne gueltigen signed_request → 403 erwartet):
curl -X POST http://localhost:8000/datadeletion -d "signed_request=invalid"

# GET-Test (ohne ID → Info-Seite):
curl http://localhost:8000/datadeletion

# GET-Test (mit unbekannter ID → 404):
curl http://localhost:8000/datadeletion?id=nonexistent

docker compose logs webhook
```
