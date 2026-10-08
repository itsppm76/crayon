# Roadmap

## Done and live (milestones M1-M6)

- [x] Telegram bot hosted on Render (free tier), long polling
- [x] Persistent memory in Neon Postgres: facts, preferences and projects recalled across chats
- [x] Gemini 2.5 Flash as the model, with Flash-Lite as fallback
- [x] Web search through Tavily, with DuckDuckGo, Mojeek and Wikipedia fallbacks, plus a page reader
- [x] Sandboxed Python code execution
- [x] Reminders and scheduled self-running jobs, delivered by a polling scheduler
- [x] Multi-day tracked tasks with subtasks, progress injection and daily check-in nudges
- [x] Confirmation before irreversible actions, secret auto-deletion, honesty guard against unbacked "done" claims
- [x] `/health` and token-protected `/selftest` endpoints
- [x] Per-user daily message cap and audit log

## Not built yet

- [ ] Read-only Gmail and Calendar tools (the OAuth helper in `core/` is unused groundwork)
- [ ] Any external write action (sending mail, creating events) with draft and approval flow
- [ ] A web adapter that shares the same agent core
- [ ] Webhook mode (polling is the deliberate current choice)
- [ ] Automated CI for the test suite

## Phase 2 status

M7 bounded goals, M8 media, M9 memory review, M10 drafts, M11 opt-in check-ins and M12 digests are deployed. M14 content-aware reactions is implemented. M13 Google Gmail/Calendar connection is awaiting account choice and OAuth setup; no Google connection is active. See TEST_CHECKLIST.md for what has and has not been tested live.
