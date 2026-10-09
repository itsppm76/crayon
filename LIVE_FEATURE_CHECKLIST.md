# Crayon: final live feature checklist

October 9, 2026. Release: per-user access update; previous runtime `e4331d3`; health version: `2.35.0`.
This is a cumulative Day 0-to-current inventory, not a promise that every feature works on every login or device. This update removes product owner/tester gates only after adding per-account isolation. External provider approval and channel limits remain.

## Accounts and web

- [x] Telegram sign-in opens the existing Telegram account, recorded chat and memory.
- [x] Identity-only Google sign-in can create an independent account without Telegram. An already linked Google identity opens its existing account. Login does not grant Gmail, Calendar or Workspace access.
- [x] Email/password registration, verification, sign-in and password-reset UI are deployed. Verified email and current disabled/revoked-token checks are required. Email identity is separate from Google identity even if the address matches.
- [x] Conventional responsive sign-in screen and readable provider-error recovery pages.
- [x] Exact-reviewed linking of an unused Google/email identity to the signed-in account; no email-based matching or silent history move.
- [x] Seven-day browser sessions, refresh/new-tab persistence, logout/expiry and recovery after temporary network/host failures.
- [x] Recorded chat pagination, visible-tab sync (about 30 seconds), typing bubble and honest waiting updates.
- [x] Ordinary web chat/upload-analysis mirrors to Telegram for Telegram-backed accounts only. Standalone accounts have no Telegram destination.
- [x] Uploads up to 20 MB, media analysis, saved analysis/metadata and generated-file activity. Raw upload bytes are temporary.
- [x] Lost upload/chat acknowledgements recover through the original request ID, not automatic repeat POSTs.
- [x] Menu for tasks, memory, notes, recorded history, activity/files and reviewed connection actions.
- [ ] Populated-account consolidation is OFF by owner choice. Separate accounts keep separate chat and memory. No production merge happened; stopped two-Google/scoped-test changes were not deployed.

## Core assistant, since Day 0

- [x] Conversational chat with persistent per-account history and memory across restarts.
- [x] Memory facts/preferences/projects; review suggestions, explicit forget and data wipe on Telegram. No automatic fact merging.
- [x] Save/list notes and contextual follow-ups.
- [x] Current-time lookup, one-off/recurring reminders, scheduled read-only prompts and cancellation on Telegram.
- [x] Tracked multi-day tasks, subtasks, todo/doing/blocked/done, recorded results, reopening, dashboard, CSV and progress-chart export.
- [x] Goal plans with bounded tool use and per-step results.
- [x] Public web search, bounded page reading and multi-source research/briefs with source receipts. Citations and synthesis can still be wrong.
- [x] Sandboxed Python maths/data checks; bounded Decimal arithmetic and unit conversion.
- [x] Dated reference currency conversion, not a live tradable FX quote or fee-inclusive price.
- [x] CSV and bar-chart PNG generation from supplied/checked data; formula escaping and size limits.
- [x] Photo, PDF, voice/audio, video and text/code analysis; common Office text/cell extraction and archive listings. Office layout/formulas/images are not verified; archives are not executed.
- [x] Review-only message drafts, complete email drafting from supplied context, optional exact wording. No invented completion or automatic third-party message send.
- [x] Opt-in proactive nudges, morning/evening digests, quiet hours and task check-ins on Telegram.
- [x] Reactions, plain-text replies, buttons, natural-language shortcuts, command menu and timed progress messages.
- [x] Public health endpoint and authenticated self-test endpoint.

## Internal work and groups

- [x] Persistent explicit background work queue: public research, bounded briefs/page reads and arithmetic,1-3 steps per job.
- [x] Queue status, Show/Pause/Resume/Cancel/Export controls, TXT reports and CSV source ledgers. Real Telegram arithmetic, completion, Show and TXT export passed.
- [x] Quiet-hour completion deferral; interrupted work blocks rather than silently repeating. Recorded task completion is not independent verification.
- [x] Tagged group public search/news; untagged messages ignored. News is dated index headlines/publishers, not verified full-article reporting.
- [x] Requester-owned group action route with per-member audience opt-in and requester-only confirmations; private ambient history stays out.
- [ ] Real group-action opt-in/confirmation and bot-add welcome acceptance remain pending. Public group news and tag/ignore paths have real checks.

## Connected-service beta

- [x] Separate per-user encrypted Gmail/Calendar OAuth connections, short personal links, status/disconnect and private intent routing. Google data bypasses Gemini and shared model memory.
- [x] Each user's own Gmail (Google currently permits named testers): search/read and bounded task+inbox-attention reports.
- [x] Exact-reviewed Gmail draft Send/Cancel with From/To/CC/BCC/subject/body, expiry, stored-draft hash checks and no uncertain-send retry. Real owner-reviewed Telegram email send passed. No email attachments.
- [x] Each user's own primary-calendar reads and exact preview/Cancel; optional guests/popup reminders are represented in the reviewed payload. No Meet.
- [x] Per-user opt-in hourly mail watch, bounded sender/subject/snippets and quiet hours. Real Telegram two-item notification passed October9 at15:00IST. Not a complete inbox audit.
- [x] Web exact session-bound one-use reviews for email/calendar/RAW Sheet writes; menu controls, not full conversational parity.
- [ ] Actual calendar Create/invitation still needs write-scope reconnect and owner-approved live acceptance. Do not infer it from preview/Cancel.
- [ ] Separate Workspace Docs text reads, Sheets bounded reads/RAW updates and public GitHub commit/PR digests exist in deployed code. Connected-provider setup and real end-to-end acceptance are not established here; do not call these fully live integrations. No Docs editing or private-repository write access.
- [ ] Public Google data-access verification remains an external gate. Identity-only login is distinct from named-tester Gmail/Calendar access.

## Computer/browser beta (all Telegram users)

- [x] Every user's computer status, arithmetic and public HTTPS browser screenshots on a bounded Codespace worker.
- [x] Per-account create/read/list text files in separate private directories; no unrestricted shell, overwrites, deletion or access to another account's files. Existing owner files stay in place.100files/account and10MB shared storage cap.
- [x] Automatic cold-start, worker readiness, calculation and idle-stop have real proof. Free quota and host/worker recovery limits remain.
- [x] Public-site screenshots with public-IP checks, sensitive-portal backstop and URL/action log. Python tutorial, Instagram login wall and signed-out YouTube were visually checked.
- [x] Fixed World Bank2024 India/China/US GDP-per-capita research-to-CSV/chart demo with record checks, findings and screenshot. Not arbitrary website automation.
- [x] Exact-reviewed controlled public-form demo available to every account: real owner preview and one Submit produced receipt/screenshot October9 at15:14IST. This is test-only, not a real booking.
- [ ] Arbitrary other users' real Telegram acceptance remains pending. Dynamic Calendly/Google appointment workflows, account login and general bookings are not accepted capabilities.

## Safety and deliberate limits

- [x] Per-account data isolation, encrypted connection/draft storage, exact one-use action reviews, audit records and bounded jobs/tools.
- [x] Secret interception/redaction, verified deletes, honesty guard and untrusted-page handling. These are safeguards, not guarantees.
- [x] No automatic external messages, purchases, paid setup or uncertain-effect retries.
- [ ] Standalone reminders/scheduled read-only jobs/work completion now use private in-app Notifications. Results persist until the next app open; no system push, email or phone alert while closed. Telegram-backed reminders still use Telegram.
- [ ] Web computer/browser and /work controls are enabled. Rooms/group actions and deletion/forget confirmations remain pending; full parity is unfinished.
- [ ] WhatsApp is parked by owner choice. No production WhatsApp service or paid Meta setup claimed.
- [ ] Free hosts sleep and APIs have shared quotas. Reminder/worker timing and uptime are best-effort. Raw historical media/private command bodies cannot be reconstructed.

## Verification ledger

-364 tests pass for the committed runtime; frontend JavaScript syntax passes. Stopped local acceptance-test changes are excluded.
- Live `/health`: database reachable, polling mode, version2.35.0. Live web status: Telegram, Google and email login configured; uploads enabled; rooms/computer disabled.
- Consolidation start rejected401 with "Account consolidation is not enabled yet." Last production environment read found no enable flag.
- Real Telegram login/history, web chat persistence and image-analysis storage were checked. Captured desktop/mobile recovery and generated full review layouts were inspected.
- Real successful standalone Google/email registration/login, password-reset delivery, and owner-device post-fix upload/reconnect acceptance were not performed by this audit. Deployed/configured is not the same as real acceptance.
- No web acceptance test sent an email, created a calendar event, wrote a Sheet or merged accounts.

[Web app](https://itsppm76.github.io/crayon/) · [Bot](https://t.me/crayon_v1_bot) · [Repository](https://github.com/itsppm76/crayon)

## Per-user rollout limits

Computer/browser/text-file commands and controlled-form previews are no longer owner/tester gated in Telegram. Computer execution keeps5 jobs/user/day,20for the existing owner,30total including failures; no budget increase. Queue owner ID comes from the authenticated caller, not user-supplied args. Old worker versions cannot handle file jobs. Machine configuration/lifecycle tokens remain private; the worker exposes only bounded operations.

Calendar and mail-watch use each user's own encrypted connection, never a fallback to the owner's account. Hourly mail checks require opt-in from that user's private Telegram chat and deliver only there; no browser-only delivery. Users who connected before calendar access was open must reconnect for their own calendar scopes. Actual provider Create and other users' live consent remain unproven. Gmail already followed each user's own connection. Google Testing still controls who can grant data scopes; product gates do not override Google approval.

## Web parity milestone

Menu now includes Work queue, Computer and Notifications. `/work list`, explicit bounded research/arithmetic plans and Show/Pause/Resume/Cancel/Export work in authenticated web chat. Public `/browse` and bounded `/computer` actions use the same private owner ID and quotas as Telegram. Standalone reminders and scheduled read-only results go to encrypted, account-bound Notifications, never an invented Telegram number. Notifications deduplicate on source receipt, check account existence and support account-bound Mark read. No OS push is promised. Local desktop/mobile UI and disposable database isolation checked; actual user acceptance remains separate.
