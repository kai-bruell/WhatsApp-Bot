# Email Retention via Proton Mail (Sieve + Auto-Delete)

Lead notification emails containing personal data (name, email, phone, reason) are automatically deleted after 30 days using Proton Mail's built-in retention mechanism.

## Setup

1. **Label**: Create a label (e.g. `lead-data`) under Settings > Folders & Labels
2. **Sieve Filter**: Route incoming lead emails to that label via Settings > Filters > Advanced (Sieve):
   ```sieve
   require ["fileinto"];
   if header :contains "subject" "Neuer Lead" {
       fileinto "lead-data";
   }
   ```
3. **Retention Rule**: Set auto-delete under Settings > Retention:
   ```
   Label: lead-data
   Delete after: 30 days
   ```

## GDPR Compliance

This ensures Art. 5(1)(e) GDPR (storage limitation) is met for email copies. Upon a deletion request (`/datenschutz` command or Meta callback), a notification is sent to `PRIVACY_EMAIL` to manually verify deletion of any remaining emails before the 30-day auto-delete.
