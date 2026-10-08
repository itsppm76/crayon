# Crayon test checklist

Covers the deployed bot (`cr_*.py`, Neon Postgres, Gemini, Tavily). Run these against a staging bot or your own chat.

Legend: **Verified live** = checked on the deployed bot through `/selftest` with synthetic users that were cleaned up afterwards (October 8, 2026). **Not live-tested** = reviewed in code only.

## Automated checks

- [ ] `GET /health` returns `{"ok": true, ...}` with `db: true`
- [ ] `POST /selftest` without a token returns `403`
- [ ] `POST /selftest` with `Authorization: Bearer <CRAYON_ADMIN_TOKEN>` runs a message through the real pipeline and returns results

```bash
curl https://crayon-v1.onrender.com/health
curl -X POST https://crayon-v1.onrender.com/selftest \
  -H "Authorization: Bearer $CRAYON_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"texts": ["hello"], "cleanup": true}'
```

`/selftest` uses a synthetic negative user id and captures replies, so nothing is sent to Telegram. Optional body fields: `reset`, `tick` (run one scheduler tick), `probe` (`reminders` or `facts`), `cleanup`.

## Feature checks

| Area | Check | Status |
| :--- | :--- | :--- |
| Memory | Tell Crayon a fact, start a new chat, ask for it back. `/memory` lists it. | Verified live |
| Memory | `/forget <key>` removes it and confirms | Verified live |
| Search | Ask for something current; the reply cites a source URL | Verified live (Tavily, with fallbacks) |
| Code | Ask for exact math; the answer comes from the sandbox | Verified live |
| Reminders | "Remind me in 2 minutes to ..." is delivered by the scheduler | Verified live |
| Scheduled jobs | "In 1 minute, search the web for ..." runs the search itself and sends the result | Verified live |
| Tracked tasks | A multi-step plan becomes a task with steps; marking a step done persists; "where are we on X?" recalls progress | Verified live |
| Task check-in | One nudge per quiet task per day, between 9am and 9pm local time | Not live-tested (needs a task untouched for 20h or more) |
| Confirmation | Forget a fact, reply NO: nothing changes. Forget again, reply YES: it is removed. | Verified live |
| Confirmation | A pending confirmation expires after 10 minutes | Not live-tested |
| Secrets | Paste something that looks like an API key or password; the message is deleted and not saved (a database search found zero stored rows) | Verified live |
| Honesty guard | The bot never says "saved" or "set" without a verified tool result in that turn | Not separately live-tested |
| Daily cap | After `CRAYON_DAILY_CAP` messages in a day the bot says the free-tier limit was reached | Not live-tested |
| Delete all | `/delete_my_data` asks for `confirm`; with it, everything is wiped and the bot reports the check | Not live-tested |

## Manual acceptance flow

1. Open [`@crayon_v1_bot`](https://t.me/crayon_v1_bot) and send `/start`, `/help`, `/memory`.
2. Tell it a preference, then ask about it in a fresh message.
3. Ask a question that needs the web and check that a source is given.
4. Set a reminder a couple of minutes out and wait for it.
5. Give it a multi-step plan, mark one step done, then ask where you stand.
6. Ask it to forget something; answer NO, then try again and answer YES.
7. Use two Telegram accounts and confirm memory never crosses users.

## Prototype tests

`pytest -q` runs the offline tests in `tests/`. They cover the original prototype code in `core/` and `tools/` with mocked model responses. They say nothing about the deployed `cr_*.py` bot.

## Phase 2

M7: `/goal <concrete research/calculation goal>` saves a 2-4 step plan and executes with up to 12 tools, repeat-call limits, and a time budget. Local runtime tests pass. Verified live: /goal calculated 17 x 23 with sandbox output, saved a note, updated both steps, and cleaned up the synthetic user. Admin form `/admin-test` uses captured output and requires the existing admin token. Selftest rejects real user IDs; scheduler excludes negative test users.

M8: photo/PDF/text/audio ingestion, 4 MB limit, untrusted-content analysis, no raw upload retention. Live image fixture verified; Telegram downloads and PDF/audio remain untested.
M9: /memory_review returns exact duplicate groups and evidence-backed preference suggestions, changes no facts. Verified live duplicate detection with two stored facts; no deletion.

M10 draft_message: review only, no external sender. M11 /proactive on|off: at most one stale-task or upcoming-reminder check-in daily. M12 /digest morning|evening|both|off and /digest_now: deterministic summaries. Defaults off, quiet hours 21-09 local; free-host delivery best-effort. Verified live with a synthetic clock: morning digest and upcoming-reminder check-in delivered once, repeat tick produced no messages. Draft fixture verified sent=false after fixing an invented excuse.

M14: content-based emoji selection and captured reaction calls. Command/YES/NO flows skipped. Telegram acceptance in a real chat not yet tested.
M8 update: synthetic PDF sentence read exactly. Real Telegram download path and actual spoken voice note not yet tested.
Runtime tests cover goal execution, invalid-tool handling, media size/type limits, duplicate detection, draft non-send, quiet hours, daily limits and reaction selection.

## Media/style expansion

- Local tests: 20 MB rejection boundary, unknown format receipt, safe ZIP listing, DOCX XML extraction, entity rejection, secret blocking, text truncation disclosure, video/caption routing, and final plain-text cleanup.
- Live verified in owner Telegram chat: new Yooooo fire reaction; photo red square + CRAYON TEST 42; immediate receipt and both timed progress lines; clean plain text; DOCX OCEAN 73; 5,880,039-byte text file LARGE 81 with truncation notice; later photo follow-up answered CRAYON TEST 42.
- Still pending live: video/large-binary Files API upload and confirmed deletion, exact 20 MB boundary, more formats. A real 15-second user MP4 (3,666,841 bytes) was read successfully through Files API; its event-ad text and summary were delivered at 22:47 IST. Independent provider deletion check remains pending.

M13 Google beta, October 8:
- 37 local tests pass, including user-bound encryption, replay, wrong-user draft access, tamper, timeout-no-retry and private-chat gate.
- Cloud client created; API enablement, scopes, Render secrets and live OAuth/read/disconnect verification still pending.
- Real email send is NOT tested; requires owner review of final recipient/content before any live send.
- Public verification and security assessment are NOT complete. No paid assessment authorized.

M15 prepared, not deployed: 41 local tests including exact group mention, ignored untagged groups, no private state and disabled group tools. Slow-text progress timer and revised prompt need owner-chat checks. Group tagging needs a real group test. Keep BotFather privacy mode ON; exact @crayon_v1_bot mentions are sufficient. No existing group was selected or messaged.
M13 2.16.0 live: health ok/db true. Privacy page visually inspected. Cloud credentials in Render; Gmail API enabled. Live captured smoke test passes /help and synthetic private-Google rejection. OAuth and real reads/send still untested; public verification not submitted.

October 8 23:15 IST live follow-up:
- 2.17.1 health ok=true/db=true.
- Personal OAuth completed; real /google_status, /gmail search (five IDs/headers), /gmail_read newsletter body and /calendar next-seven-days passed in owner's DM.
- Real one-line /email_draft self-addressed review-only fixture displayed exact content/hash; /email_cancel answered no send. Real send not tested; owner has a separate draft that was not touched by these tests.
- Slow text response delivered progress before clean final answer; revised prompt inspected on one HTTP/HTTPS sample, not a quality benchmark.
- BotFather says privacy ENABLED, with username mentions delivered. Left unchanged. Real group delivery not yet tested; no group chosen or messaged.
- Public Google verification not submitted; testing status remains. No payment/assessment initiated.

2.17.2: live health good, exact-content draft buttons visually inspected, Cancel callback passed in owner DM without send. Search Console URL-prefix ownership verification succeeded by homepage HTML tag. This is not OAuth app approval. Verification submission remains pending its end-to-end sanitized demo. No production publish, paid assessment or real test send initiated. His separately entered draft was left untouched.
