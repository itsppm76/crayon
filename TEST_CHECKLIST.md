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
| Code | Ask for exact math; the answer comes from the sandbox | Not separately live-tested |
| Reminders | "Remind me in 2 minutes to ..." is delivered by the scheduler | Verified live |
| Scheduled jobs | "In 1 minute, search the web for ..." runs the search itself and sends the result | Verified live |
| Tracked tasks | A multi-step plan becomes a task with steps; marking a step done persists; "where are we on X?" recalls progress | Verified live |
| Task check-in | One nudge per quiet task per day, between 9am and 9pm local time | Not live-tested (needs a task untouched for 20h or more) |
| Confirmation | Forget a fact, reply NO: nothing changes. Forget again, reply YES: it is removed. | Verified live |
| Confirmation | A pending confirmation expires after 10 minutes | Not live-tested |
| Secrets | Paste something that looks like an API key or password; the message is deleted and not saved | Not live-tested in Telegram |
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
