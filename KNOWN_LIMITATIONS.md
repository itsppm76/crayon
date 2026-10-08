# Known limitations

Status is intentionally conservative. This file reflects the deployed bot (`cr_*.py` modules, Neon Postgres, Render free tier).

- **Free hosting:** Render's free instance sleeps when idle and can be slow on a cold start. A keep-warm ping reduces this but does not guarantee uptime.
- **Reminder timing:** reminders and jobs are delivered by an in-process polling scheduler. Delivery is close to the due time, not exact, and is delayed if the host is down.
- **Free-tier quotas:** Gemini, Tavily and Neon have free-tier limits. A per-user daily message cap (default 80) is in place to stay inside them.
- **Search quality:** results depend on Tavily and its fallbacks. Snippets can be stale or wrong, and page text is treated as untrusted data.
- **Code sandbox:** no network, files or access to user data, by design. It is for exact math and checks, not data fetching.
- **Heuristic safety:** secret detection and the honesty guard are pattern-based checks, not guarantees. If a real secret is pasted into a chat, rotate it.
- **Model mistakes:** the model can misread dates, time zones or intent. Confirm reminders and task details when they matter.
- **External writes:** reviewed Gmail drafts can be sent only after exact recipient/content confirmation. No automatic sends, calendar creation, third-party outreach or purchases.
- **Google integrations:** live per-user OAuth is in `cr_google.py`; the older `core/` helper is unused.
- **Prototype leftovers:** `core/`, `adapters/`, `tools/`, `db/schema.sql` and the Colab notebook are from the first prototype. The offline tests in `tests/` cover that code and mock model calls.

Phase 2 limits: goals are bounded tool workflows, not unrestricted autonomous browser agents. Media downloads cap at 20,000,000 bytes. Common photos, PDF, audio and video use Gemini; large media/video uses temporary Files API uploads with best-effort immediate deletion and a warning if deletion fails (provider auto-expiry: 48 hours). Office files are text/cell extraction only, bounded to 24,000 characters; layout/images/formulas are not verified. ZIP/TAR archives get listings only, never execution/extraction. Unknown formats are acknowledged but not decoded. A short media analysis summary is retained in chat history for follow-ups; raw files are not saved locally. Memory review does not auto-merge facts. Drafts do not send. Proactive check-ins and digests are opt-in and depend on the host running. Per-user Google beta is active for named testers.

Google beta accepts natural-language private-chat requests plus optional slash commands. Only user intent is parsed by the model; Google results bypass it. Calendar reads primary only, next seven days. Gmail reads five search results and bounded plaintext bodies. Email drafts allow one recipient, no CC/BCC/attachments; ten-minute confirmation, no uncertain-send retries. Testing mode limits access to named users and refresh tokens can expire after seven days. Public verification is pending; a paid restricted-scope assessment must be reported, never initiated.

Phase3 (2.20.1): public HTTP link reading, no JavaScript/login/paywall bypass, 1MB/12k-character caps, redirect private-host checks. Research retrieves bounded sources and labels failures; source coverage and model citation quality remain fallible. Currency is dated reference data, not a live quote; fees excluded. Unit conversion is fixed Decimal arithmetic with bounded supported units. Weather remains search-based; no Open-Meteo tool.

Capacity is not load-tested. Six update workers, per-user serialization; sustained requests hit model quotas first. Current Crayon free project: primary3.5 Flash Lite15RPM/250k inputTPM/500RPD, fallback3.1 Flash Lite15/250k/500, fallback3 Flash5/250k/20. Limits are project-wide, can change, and model/verification/memory/tool workflows consume several calls per reply. Multiple keys in one project do not increase quota. Render Free0.1CPU/512MB; no uptime guarantee.

2.21 files: CSV/bar-chart generation is bounded to user-requested exports and supplied/verified data, no generated server code. CSV formulas are escaped, charts support non-negative values only. Pillow renders at1000px;12bars max. Attachments use Telegram sendDocument,2MB max/two per response. No hosted public artifacts. Short Google connection URL validates existing unused10-minute state and uses fixed Google endpoint/config. Never forward account-bound links; friends must request their own.

Computer/browser beta: owner-only Codespaces2-core machine, outbound worker bridge, fresh public-web Chromium with public-IP checks and known sensitive-portal hostname/path deny rules, not a perfect category classifier. No automatic machine wake, no shell/eval/imports through the bot, no other user's access to the owner's GitHub-bearing machine. Worker session caps25minutes. Text files restricted to one dedicated directory with no overwrite/delete/symlink access. Browser two-page cap, GET-only requests, no credentials/forms/accounts/transactions/downloads. Screenshot is a viewport capture, not a guarantee of correct page content. Codespaces incurs storage usage even while stopped;180core-hours equals about90hours at2cores. Stop when finished and keep the$0 paid budget blocked.

Tester beta: owner+approved-tester UID gate;5 execution jobs per tester/day,20 owner/day,30 total/day, atomically reserved before jobs including failures. No automatic wake. Additional testers are not enabled until their Telegram IDs are verified.102 local tests, tester behavior code-tested, no impersonation or live test from another person's chat.

World Bank chart chain is one fixed recipe (India/China/USA,2024 nominal GDP per capita), not arbitrary autonomous research. Exact records validated before outputs. Instagram login wall and YouTube signed-out homepage screenshot passed; authenticated browsing, search and playback are not claimed.
