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

## Google login addition (October 9, 21:22 IST)

- Dedicated Google OIDC client with basic identity scopes, state/cookie/nonce/S256 PKCE, signed token checks.
- Explicit session-bound review links stable Google subject to existing Telegram UID; no email matching, account merge or silent integration permissions.
- Unlinked users start with Telegram and link once; Google external Testing restrictions remain.
- 326 local tests passed. Dedicated login configuration and backend/Pages rollout verified; real Google account picker reached. Callback permits inert Google-returned metadata without trusting it.
- Cloud Audience confirmed external Testing with existing testers. Real owner exact link and subsequent Google login returning the same UID/history remain pending. No identity linked or provider data-access granted by this rollout.

- Scope correction: Google documents an allowlist exception for basic identity-only login in Testing. Earlier blanket named-tester login wording was too broad; Gmail/Calendar data-access tester limits are separate. See https://developers.google.com/identity/protocols/oauth2/production-readiness/overview .

## Isolated public Google login (October 9, 21:36 IST)

- Owner picked separate identity-only production project. Existing Gmail/Calendar Testing project unchanged.
- New login project published; only openid/email/profile declared, no sensitive/restricted verification required. Branding is unverified, not a certified-app claim.
- Existing login behavior is still Telegram-first and explicitly reviewed linking. Google/email-first accounts and later reviewed merge are new requested work, not shipped here.
