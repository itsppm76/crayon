# Crayon web release checklist

Updated October 9, 2026, 21:22 IST. Built, deployed and real-device acceptance are separate.

## Done and deployed

- [x] Web frontend is in this repository and hosted on GitHub Pages.
- [x] Dedicated identity-only Google OIDC sign-in and exact session-bound Telegram/Google linking deployed. No email matching or automatic account merge. External Testing only.
- [x] Telegram OIDC login maps to the existing Telegram user, memory and recorded history.
- [x] New sessions last seven days. Refresh and new tabs restore the same browser login. Logout and server expiry revoke access. Browser storage deletion, private browsing and account deletion can also end access.
- [x] Saved login reconnects after temporary host/network failures instead of giving up at the first failed fetch.
- [x] Latest recorded history refreshes within about 30 seconds while the tab is visible, and on return to the tab. Older-page browsing is preserved.
- [x] Ordinary web chat/replies and upload analysis mirror to the authenticated user's Telegram DM. Transport failure is reported without automatic resend.
- [x] Typing bubble and delayed waiting updates show during web chat and upload processing. They stop on result, error or logout; no invented completion/progress claims.
- [x] Uploads support up to 20 MB. Raw files are temporary; analysis/metadata can remain in history. Generated web files can be recovered from Web activity / files.
- [x] Lost upload acknowledgements and temporary result-fetch failures recover by checking the original request ID. Upload/chat POSTs are never automatically repeated.
- [x] Web menu has tasks, memory, reminders, recorded history, activity/files and connections/actions.
- [x] Google reads bypass AI and shared model memory. Email/calendar/Sheet writes require a session-bound, one-use exact review. Each member uses their own connection; calendar beta remains owner-only.
- [x] Private Telegram command paths now add encrypted generic display receipts when ordinary history was not stored. Private command bodies/results are not silently copied into model memory.
- [x] Upload authentication errors return readable JSON and allowed-origin CORS.
- [x] Frontend script is versioned to avoid ten-minute stale-script caching on reload.
- [x] README, release checklist, limitations, roadmap, test notes and changelog reflect this release.

## Evidence, not promises

- 326 local Python tests passed.
- Captured browser tests: same-browser refresh/new tab; transient saved-session fetch failure and automatic reconnect; one failed upload acknowledgement plus one failed result GET recovered with exactly one POST; delayed typing update and logout cleanup.
- Desktop and 390px mobile screenshots inspected, with no horizontal overflow in captured checks.
- Real owner Telegram login and existing-history mapping passed. Real owner web chat persisted. The owner's 5.39 MB image reached the server at 20:04:24 and analysis completed at 20:04:50; browser result delivery failed before recovery was shipped.
- Seven-day session remains in the database across deployment. Backend recovery release is live; Pages has reconnect and recovery code.
- Live /web/status confirms Google login configured; unauthenticated link-start is401. Real Google account chooser reached with basic identity scopes. Owner personal/college Google accounts are existing testers. No Google identity was silently linked.
- No real email/calendar/Sheet mutation was performed for these web acceptance checks.

## Still pending

- [ ] Real owner exact Google link approval, then Google logout/login returning the same UID/history. Live Google picker reached; full callback/link/login acceptance is not yet proved.
- [ ] Owner-device post-fix reconnect, upload-result delivery and live two-way chat acceptance.
- [ ] Full conversational parity: Google/email/calendar/Workspace workflows should behave consistently across both interfaces, while preserving exact review and channel privacy. Current web workflow uses the menu.
- [ ] Web internal-work queue controls and full Telegram command/menu coverage.
- [ ] Richer shared attachment history. Historical raw Telegram media and omitted command bodies were never retained and cannot be reconstructed.
- [ ] Web-visible reminder delivery/notifications and background completion updates. Existing reminders still arrive in Telegram, with free-host timing limits.
- [ ] General provider booking/account workflows and broad public Google verification. Existing narrow controlled-form proof is not general booking support.

## Deliberately locked, not broken

- Web rooms/group actions: no shared-audience interface yet. Telegram group consent rules must carry over before enabling it.
- Web computer/browser execution: approved-tester beta in Telegram only; web allowlist/review/transport not yet wired.
- Web deletion/forget confirmations: disabled until dedicated exact-review controls prevent cross-channel approvals. Telegram deletion remains available.
- Automatic external sends, automatic uncertain-action retries, paid tiers and payment setup: not enabled.
- WhatsApp: parked by owner request. Test configuration is preserved; no card/payment method or paid tier was added.

## Retest without reuploading the old image

1. Open the current Pages build, let the saved session reconnect, and confirm the name is correct.
2. Open Menu > Web activity / files for the saved image analysis, or recorded history.
3. Send one small new image. Confirm one completed analysis and no duplicate Telegram mirror.
4. Send one ordinary Telegram message and one ordinary web message. Confirm the latest conversation updates on both surfaces.
5. Close/reopen the same browser and confirm login restores. Log out on shared devices.

Full parity is the target, not a completed claim. Free-host restart, network outages and model/provider quotas still affect timing.

## One-time Google login linking

1. Sign in with Telegram and check the existing account name/history.
2. Menu > Link Google login. Choose the Google account you want to use.
3. Return to Crayon and review the exact Telegram ID/name and verified Google email. Link only if both are yours.
4. Log out, use Log in with Google, and check that the same recorded history returns.

This login does not authorize Gmail, Calendar or Workspace access. The current Google app accepts named test users only; publishing for everyone remains separate work.
