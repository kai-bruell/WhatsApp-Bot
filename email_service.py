import asyncio
import json
import os
import ssl
import aiosmtplib
from email.message import EmailMessage
from config import Config


def _tls_context():
    """Build TLS context. Skips cert verification for self-signed certs (e.g. Proton Bridge)."""
    if Config.SMTP_VERIFY_TLS:
        return None  # aiosmtplib default
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


async def send_lead_email(ctx, lang):
    """Send lead notification email to owner. Returns (success, error_reason)."""
    if not all([Config.SMTP_HOST, Config.SMTP_USER, Config.SMTP_PASS, Config.SMTP_FROM]):
        return False, "SMTP nicht konfiguriert" if lang == "de" else "SMTP not configured"

    phone_line = ctx.get("contact_number") or ("-" if lang == "en" else "–")

    msg = EmailMessage()
    msg["Subject"] = f"Neuer Lead: {ctx.get('name')}"
    msg["From"] = Config.SMTP_FROM
    msg["To"] = Config.CONTACT_EMAIL
    msg.set_content(
        f"Neuer Lead über WhatsApp-Bot\n"
        f"{'=' * 30}\n\n"
        f"Name:    {ctx.get('name')}\n"
        f"E-Mail:  {ctx.get('email')}\n"
        f"Telefon: {phone_line}\n"
        f"Grund:   {ctx.get('reason')}\n"
    )

    try:
        await aiosmtplib.send(
            msg,
            hostname=Config.SMTP_HOST,
            port=Config.SMTP_PORT,
            username=Config.SMTP_USER,
            password=Config.SMTP_PASS,
            start_tls=True,
            tls_context=_tls_context(),
            timeout=10,
        )
        return True, None
    except aiosmtplib.SMTPAuthenticationError:
        reason = "SMTP-Authentifizierung fehlgeschlagen" if lang == "de" else "SMTP authentication failed"
    except aiosmtplib.SMTPConnectError:
        reason = "SMTP-Verbindung fehlgeschlagen" if lang == "de" else "SMTP connection failed"
    except asyncio.TimeoutError:
        reason = "SMTP-Timeout" if lang == "de" else "SMTP timeout"
    except Exception as e:
        reason = str(e)[:80]

    print(f"Email send failed: {reason}")
    return False, reason


async def send_privacy_email(email_type, lead_data):
    """Send privacy-related email (deletion request or reminder) to PRIVACY_EMAIL."""
    if not Config.PRIVACY_EMAIL:
        print("PRIVACY_EMAIL not configured, skipping privacy email")
        return False

    if not all([Config.SMTP_HOST, Config.SMTP_USER, Config.SMTP_PASS, Config.SMTP_FROM]):
        print("SMTP not configured, skipping privacy email")
        return False

    template_path = os.path.join(Config.LANG_DIR, "privacy-deletion-request.json")
    with open(template_path, "r", encoding="utf-8") as f:
        templates = json.load(f)

    tpl = templates[email_type]

    name = lead_data.get("name") or lead_data.get("lead_name") or "–"
    email = lead_data.get("email") or lead_data.get("lead_email") or "–"
    phone = lead_data.get("phone") or "–"
    reason = lead_data.get("reason") or "–"
    trigger = lead_data.get("trigger") or "–"

    subject = tpl["subject"].replace("$NAME", name)
    body = (tpl["body"]
            .replace("$NAME", name)
            .replace("$EMAIL", email)
            .replace("$PHONE", phone)
            .replace("$REASON", reason)
            .replace("$TRIGGER", trigger))

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = Config.SMTP_FROM
    msg["To"] = Config.PRIVACY_EMAIL
    msg.set_content(body)

    try:
        await aiosmtplib.send(
            msg,
            hostname=Config.SMTP_HOST,
            port=Config.SMTP_PORT,
            username=Config.SMTP_USER,
            password=Config.SMTP_PASS,
            start_tls=True,
            tls_context=_tls_context(),
            timeout=10,
        )
        print(f"Privacy email ({email_type}) sent to {Config.PRIVACY_EMAIL}")
        return True
    except Exception as e:
        print(f"Privacy email send failed: {e}")
        return False
