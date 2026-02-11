# WhatsApp Webhook Bot

A WhatsApp chatbot built with FastAPI that handles incoming messages via the Meta Cloud API. Features include multi-language support (DE/EN), rate limiting, contact management via CardDAV (Radicale), and vCard generation.

## Quick Start

```bash
# 1. Clone the repository
git clone <repo-url> && cd meta

# 2. Copy the example environment file and fill in your values
cp .env.example .env

# 3. Build and start the container
docker compose up -d

# 4. Verify the webhook is running
curl "http://localhost:8000/webhook?hub.mode=subscribe&hub.verify_token=YOUR_VERIFY_TOKEN&hub.challenge=test"
# Expected response: test

# 5. Check the logs
docker compose logs -f webhook
```

## Configuration

All settings are managed via environment variables in `.env`. See `.env.example` for available options:

| Variable | Description |
|---|---|
| `VERIFY_TOKEN` | Meta webhook verification token |
| `WHATSAPP_TOKEN` | Meta WhatsApp Cloud API system token |
| `PHONE_NUMBER_ID` | WhatsApp Business phone number ID |
| `APP_SECRET` | Facebook App Secret (for data deletion callback signature validation) |
| `CONTACT_MOBILE` | Mobile number shown in welcome message |
| `CONTACT_LANDLINE` | Landline number shown in welcome message |
| `CONTACT_EMAIL` | Email address shown in welcome message |
| `RADICALE_URL` | Radicale CardDAV server URL |
| `RADICALE_USER` | Radicale username |
| `RADICALE_PASSWORD` | Radicale password |
| `RATE_*` | Rate limit thresholds (see `.env.example`) |

## Project Structure

```
meta/
├── docker-compose.yml      # Container orchestration
├── .env.example            # Environment variable template
├── docs/                   # Documentation
└── webhook/                # Application source
    ├── Dockerfile
    ├── requirements.txt
    ├── main.py             # Uvicorn entrypoint
    └── app/
        ├── api.py          # FastAPI routes
        ├── bot_logic.py    # Message handling logic
        ├── config.py       # Environment configuration
        ├── messenger.py    # WhatsApp API client
        ├── i18n.py         # Internationalization (DE/EN)
        ├── radicale.py     # CardDAV integration
        ├── vcard.py        # vCard generation
        ├── rate_limit.py   # SQLite-based rate limiter
        ├── data_deletion.py # Meta data deletion callback
        └── lang/           # Translation files
```

## Data Deletion Callback

Meta requires a Data Deletion Callback URL for platform apps. When a user removes the app via Facebook, Meta sends a signed `POST /datadeletion` request. The server validates the signature, stores the deletion request, and returns a status URL.

- **`POST /datadeletion`** — Server-to-server callback from Meta (validates `signed_request` via HMAC-SHA256)
- **`GET /datadeletion?id=CODE`** — HTML status page showing deletion confirmation

Requires `APP_SECRET` to be set in `.env`.

## Useful Commands

```bash
docker compose up -d          # Start in background
docker compose down            # Stop and remove containers
docker compose up -d --build   # Rebuild and restart
docker compose logs -f webhook # Follow logs
```
