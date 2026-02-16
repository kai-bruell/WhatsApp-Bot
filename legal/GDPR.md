# GDPR Compliance Measures

## Personal Data Collected

The bot collects the following personal data during the lead flow:
- Name
- Email address
- Phone number (optional)
- Reason for inquiry

This data is stored in the SQLite database (`leads` table) and sent via email to the owner (`CONTACT_EMAIL`).

## Data Retention (Art. 5(1)(e) GDPR)

### Database
- The cleanup scheduler (`cleanup.py`) runs periodically inside the container and deletes old DB entries (`leads`, `email_log`) after the configured retention period (default: 30 days).
- Configured via `DATA_RETENTION_TIME` (e.g. `30d`, `1h`, `5m30s`).

### Email Copies
- Lead notification emails are automatically labeled and deleted after 30 days via Proton Mail Sieve filters and retention rules.
- See `legal/SLIEVE.md` for setup details.

## Right to Erasure (Art. 17 GDPR)

Two deletion triggers exist:

| Trigger | How | What happens |
|---------|-----|--------------|
| **User** | `/datenschutz` or `/privacy` bot command | User confirms via button -> DB data deleted, deletion request email sent to `PRIVACY_EMAIL` |
| **Meta callback** | `/data-deletion` endpoint | Meta sends signed request when user deletes WhatsApp -> DB data deleted, deletion request email sent to `PRIVACY_EMAIL` |

In both cases:
1. `sessions` and `leads` entries are deleted from the database immediately
2. `email_log` entries are marked as `deletion_requested`
3. A deletion request email is sent to `PRIVACY_EMAIL` to verify removal of email copies
4. The email states whether it was triggered by the user or by Meta

## Audit Trail

The `email_log` table tracks:
- Which personal data was sent via email (name, email, phone, reason)
- When it was sent (`sent_at`)
- When deletion was requested (`deletion_requested_at`)
- Whether deletion was requested at all (`deletion_requested`)
