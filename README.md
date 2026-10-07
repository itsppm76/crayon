# Crayon v1

> **A free, open-source personal AI assistant for Telegram.** Friendly, short replies; read-only Google access; approval before external writes.

<div style="background:#FFC93C;color:#2B2D31;padding:12px;border-radius:8px"><strong>Crayon Yellow #FFC93C</strong> · Charcoal #2B2D31 · Slate #6B7280 · Light grey #F3F4F6</div>

## What is implemented

- Python core separated from Telegram (`core/`, `adapters/telegram/`, future `adapters/web/`)
- Ollama-first model router, then OpenRouter `:free` models, then Gemini
- Per-user in-memory prototype memory and Supabase schema
- Basic tools: time, notes, reminders
- `/delete_my_data` and approval-button scaffolding
- Google OAuth helper with Calendar/Gmail read-only scopes
- Colab launcher and tests

## BotFather copy

- **Name:** Crayon v1
- **Description:** A friendly personal AI assistant for notes, reminders, and read-only calendar and Gmail help.
- **About:** Crayon v1 — your private, approval-first assistant.

## Setup

### 1. Telegram
1. Open `@BotFather`, run `/newbot`, choose a name and username.
2. Copy the bot token into a local `.env` or Colab Secret named `TELEGRAM_BOT_TOKEN`.
3. Do not commit the token.

### 2. Supabase free tier
1. Create one Supabase project (do not create multiple projects for credits).
2. Run [`db/schema.sql`](db/schema.sql) in SQL Editor.
3. Put the project URL and server-side service-role key in environment variables. Never expose the service-role key to a browser or Telegram.
4. **Prototype note:** the included tests use in-memory memory; wire a Supabase repository before production persistence.

### 3. Model backends
- Install Ollama and pull `gemma4:e4b` where available. The exact model availability can change; if the pull fails, set another local Ollama model in `OLLAMA_MODEL`.
- Add optional OpenRouter key and only `:free` model IDs in `OPENROUTER_MODELS`.
- Add optional Gemini AI Studio key for the final fallback.
- Never print or hardcode secrets.

### 4. Google OAuth (testing mode)
1. In Google Cloud Console, create one OAuth client for a Desktop app.
2. Enable Gmail API and Google Calendar API.
3. Add yourself as a test user while the consent screen is in testing mode.
4. Download the client JSON to `config/google_client_secret.json` (keep it out of git).
5. `/connect` route wiring is **UNTESTED** in this prototype; use `core/google_oauth.py` as the safe starting point. It requests only `calendar.readonly` and `gmail.readonly`.

### 5. Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env using your own credentials
python main.py
```

### 6. Run in Colab
Open [`notebooks/crayon_v1.ipynb`](notebooks/crayon_v1.ipynb), replace `YOUR_USERNAME` with your repository URL, add secrets in Colab's Secrets panel, and run cells top-to-bottom. The free T4 runtime may disconnect; keep the notebook tab open.

## Tests

```bash
pytest -q
```

Tests are deliberately offline and use mocked transports; they do not prove Telegram, Ollama, Google, Supabase, OpenRouter, or Gemini connectivity.

## Architecture

```text
Telegram long polling -> adapters/telegram -> core.Agent -> model router
                                                   |-> local Ollama
                                                   |-> OpenRouter free rotation
                                                   |-> Gemini free fallback
                                                   |-> memory/tools
```

## Security posture

- No Google passwords; OAuth only.
- External text is untrusted data, not instructions.
- Read-only Google scopes.
- User ID is passed through every memory operation.
- External writes must remain draft-only until approval; current adapter logs approval but intentionally does not perform external writes.
- Maximum tool-loop policy is defined in `Agent`; production tool execution should enforce it at every tool dispatch.

## License

MIT. See [`LICENSE`](LICENSE).
