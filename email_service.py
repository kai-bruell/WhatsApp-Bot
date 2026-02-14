import aiosmtplib
from email.message import EmailMessage
from config import Config


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
