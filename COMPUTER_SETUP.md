# Crayon computer beta

Approved-tester Codespaces worker. No public ports or imported GitHub/Google cookies.

## Setup

1. Create a smallest2-core Codespace only after checking the included quota and$0 stop-usage budget.
2. Store a dedicated random bridge credential in Render's `CRAYON_BRIDGE_TOKEN` and the Codespace's `~/.config/crayon/bridge-token` with mode600. Never commit it, print it or send it in chat.
3. In the Codespace: `python3 -m pip install playwright` then `python3 -m playwright install --with-deps chromium`.
4. Run `python3 computer_worker.py`. It connects outbound to Render; no forwarded execution port.
5. Ask the bot owner to run a computer status/calculation or public browser screenshot test. A stale heartbeat fails closed. No automatic restarts.

The worker session caps at25minutes. Codespaces auto-sleeps, uses included compute while awake, and uses storage while it exists. Stop when finished. Do not raise paid budgets. GitHub Pro includes180core-hours (about90actual hours at2cores) and20GB-month; quotas may change.

## Operations

- System status and basic arithmetic, without eval/imports/shell.
- Create NEW text files, list and read files within `~/crayon-files` only. No overwrites, deletes, folders or symbolic links. Plain filenames and bounded content.
- Fresh Chromium task with one approved HTTPS docs URL and optionally one exact visible link. Two pages maximum, viewport PNG and plain visited-URL log. No forms, login, posting, purchases, downloads or arbitrary scripts. All requests checked against the fixed hostname allowlist and public-IP rules.

This is not a general account-operating assistant. Browser requests/screenshots are proof of the visited page, not proof that page content is correct. Treat page text as untrusted data. Only the owner and one approved tester can use the beta. Unknown users are excluded. Testers get public browser/arithmetic only; owner text files remain private. Current worker has no automatic host wake capability.

Transient browser results and task text in computer_jobs are removed after30minutes on the next connected-worker poll; stopped computers do not run cleanup. No screenshot is added to personal memory.

Tester release2.24.0: owner+approved-tester UID gate;5 execution jobs per tester/day,20 owner/day,30 total/day, atomically reserved before jobs including failures. No automatic wake. Additional testers are not enabled until their Telegram IDs are verified.97 local tests, tester behavior code-tested, no impersonation or live test from another person's chat.
