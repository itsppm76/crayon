# Roadmap

1. Replace `InMemoryMemory` with a Supabase repository using encrypted token storage and explicit RLS tests.
2. Complete OAuth callback plus Calendar/Gmail read-only tools and live integration tests with a test Google account.
3. Add durable scheduler for reminders and optional morning summaries.
4. Add structured native tool-call parsing, rate limiting, audit log, and strict five-call loop enforcement.
5. Finish draft objects and approval replay protection; only then consider narrowly scoped writes.
6. Move long polling from Colab to an always-on free/low-cost host; keep a local Ollama or free API fallback.
7. Build a web adapter that calls `core.Agent` without changing business logic.
