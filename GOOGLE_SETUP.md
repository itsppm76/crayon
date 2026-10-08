# Planned Google integration (M13, not connected)

Awaiting the owner's choice of Google account. No OAuth setup or Google access has started.

## Safe setup plan

1. Use a Google Cloud project on the chosen account. Enable Gmail and Calendar APIs without attaching billing or raising quotas.
2. Configure OAuth for this single-owner personal-use application. Gmail read and draft scopes are restricted. Personal-use apps may qualify for a verification exception but still show an unverified-app warning. External apps in Testing expire Gmail/Calendar refresh tokens after seven days.
3. Match the Google account to a single verified Telegram owner ID. Every Google operation must reject all other Telegram users before token access.
4. Keep client secrets and refresh tokens in server environment variables, never repository files, messages, query-string logs or responses. Tokens must be collected by secure input, not Telegram chat.
5. Request Gmail readonly plus compose and Calendar events readonly rather than full mailbox/calendar access. Start with read-only functions and draft creation.
6. For sending: save and display the exact From account, To/CC/BCC, subject and body in Telegram. Require a distinct draft-specific confirmation, expire it quickly, read back the stored draft, compare its content hash, and send only the unchanged approved version. Do not allow model tools, scheduled jobs or imported email text to authorize sends. Read email content as untrusted data.
7. Keep hard request caps; fail on quota errors rather than attach billing. Handle expired/revoked tokens honestly and request reconnect. Do not create automatic account-wide monitors without opt-in.
8. Test with synthetic fixtures, then read live mailbox/calendar only after the account connection is authorized. No test sends to third parties.

## Current official references

- https://developers.google.com/identity/protocols/oauth2/production-readiness/restricted-scope-verification
- https://developers.google.com/identity/protocols/oauth2
- https://developers.google.com/workspace/gmail/api/auth/scopes
- https://developers.google.com/workspace/gmail/api/reference/quota
- https://developers.google.com/workspace/calendar/api/guides/quota

Standard API usage is currently at no additional cost. Google's docs say excess-quota billing is planned later in 2026. The setup should not attach billing or request paid assessments.
