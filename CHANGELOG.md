# Change log

## October 9, 2026 - web release and recovery

- GitHub Pages frontend and Telegram OIDC identity mapping to existing member records.
- Seven-day server sessions, same-browser persistence and explicit logout/expiry.
- Recorded history pagination, visible-tab refresh and same-user Telegram mirrors for ordinary chats/upload analysis.
- Encrypted generic command receipts, kept outside model memory. No historical-body reconstruction.
- Uploads up to 20 MB, temporary raw bytes, saved analysis and generated-file activity.
- Exact, session-bound one-use review for web email/calendar/RAW Sheet writes. Private Google reads bypass AI/history.
- Typing bubble and 12/30/60-second honest waiting updates, cleared on result/error/logout.
- Lost POST acknowledgements/result-fetch failures recover by safe GET checks of the original request ID. No automatic resubmission.
- Allowed-origin CORS on upload authentication errors.
- Saved-session reconnect after transient failures and versioned frontend script caching.
- 317 local tests passed; captured desktop/mobile checks. Owner-device post-fix recovery acceptance pending.

See [release checklist](WEB_RELEASE_CHECKLIST.md) for remaining parity work and deliberately locked features. No paid tier/payment setup, no acceptance-test email/calendar/Sheet write.

## Google login addition (October 9, 21:16 IST)

- Dedicated Google OIDC client with basic identity scopes, state/cookie/nonce/S256 PKCE, signed token checks.
- Explicit session-bound review links stable Google subject to existing Telegram UID; no email matching, account merge or silent integration permissions.
- Unlinked users start with Telegram and link once; Google external Testing restrictions remain.
- 325 local tests passed. Configuration rollout and real owner link/login acceptance still pending at this checkpoint.
