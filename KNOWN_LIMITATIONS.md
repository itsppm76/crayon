# Known limitations

Status is intentionally conservative. This file reflects the deployed bot (`cr_*.py` modules, Neon Postgres, Render free tier).

- **Free hosting:** Render's free instance sleeps when idle and can be slow on a cold start. A keep-warm ping reduces this but does not guarantee uptime.
- **Reminder timing:** reminders and jobs are delivered by an in-process polling scheduler. Delivery is close to the due time, not exact, and is delayed if the host is down.
- **Free-tier quotas:** Gemini, Tavily and Neon have free-tier limits. A per-user daily message cap (default 80) is in place to stay inside them.
- **Search quality:** results depend on Tavily and its fallbacks. Snippets can be stale or wrong, and page text is treated as untrusted data.
- **Code sandbox:** no network, files or access to user data, by design. It is for exact math and checks, not data fetching.
- **Heuristic safety:** secret detection and the honesty guard are pattern-based checks, not guarantees. If a real secret is pasted into a chat, rotate it.
- **Model mistakes:** the model can misread dates, time zones or intent. Confirm reminders and task details when they matter.
- **No external writes:** the live bot does not send email, create calendar events or contact third parties.
- **Google integrations:** the OAuth helper in `core/` is unused and not wired into the bot.
- **Prototype leftovers:** `core/`, `adapters/`, `tools/`, `db/schema.sql` and the Colab notebook are from the first prototype. The offline tests in `tests/` cover that code and mock model calls.

Phase 2 limits: goals are bounded tool workflows, not unrestricted autonomous browser agents. Media uploads have a 4 MB cap; document/image/audio fidelity varies. Memory review does not auto-merge facts. Drafts do not send. Proactive check-ins and digests are opt-in and depend on the host running. No Google connection is active yet.
