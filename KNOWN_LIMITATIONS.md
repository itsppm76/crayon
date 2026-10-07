# Known limitations

Status is intentionally conservative.

- **Colab sessions time out:** long polling stops when the runtime sleeps or disconnects; there is no persistence in the included in-memory implementation.
- **Persistence wiring is incomplete:** `db/schema.sql` is ready, but a Supabase repository and token encryption adapter are **UNTESTED**.
- **Google integrations are incomplete:** OAuth helper and read-only scopes exist; `/connect`, Calendar reads, Gmail summaries, and token storage are **UNTESTED**.
- **Model availability varies:** `gemma4:e4b` may not be available in every Ollama registry/runtime. The router fallback is tested only with mocked HTTP responses.
- **Free-tier limits apply:** OpenRouter free models can impose 20 requests/minute, daily caps, queueing, and 429 responses; Gemini quotas also vary. Rotation is implemented, but production quota behavior is **UNTESTED**.
- **Small-model mistakes:** local models can misunderstand dates, tool arguments, or malicious content. Keep approval gates and review outputs.
- **Telegram/Google verification:** Google OAuth verification and publishing requirements may apply before public release.
- **No production webhook:** Telegram runs long polling in the prototype; webhook deployment is a future step.
- **No external writes:** approval buttons are scaffolded, but current code does not send mail, create events, or contact third parties.
- **Not free:** a continuously running reliable host, production database usage beyond free limits, paid model quotas, and Google verification-related operational work may cost money. Free alternatives are Colab, Ollama, Supabase free tier, OpenRouter `:free` models, and Gemini free tier subject to limits.
