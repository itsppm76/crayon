# Free fallback resilience

Crayon 2.36.0 keeps Gemini primary. When Gemini reports quota, availability, auth or missing-model trouble, eligible requests use OpenRouter only if OPENROUTER_AUTO_FALLBACK=on and OPENROUTER_API_KEY is set.

No Groq integration or key reuse. Use a dedicated Crayon key with a provider-side $0 credit limit on a free account. Never use Shayari credentials, add credits or upgrade a plan.

## Fallback order

1. nvidia/nemotron-3-ultra-550b-a55b:free
2. cohere/north-mini-code:free
3. nvidia/nemotron-3-super-120b-a12b:free
4. openrouter/free
5. One retry of openrouter/free after a half-second pause.

Each route must appear in the provider's current model catalog with prompt and completion prices present and all listed pricing components exactly zero. Nested pricing is checked too. Catalog checks fail closed and cache for at most five minutes. Missing tool/JSON support skips that model. Requests carry zero maximum prompt/completion/request/image/audio prices, data_collection=deny and require_parameters=true. Each SDK call has no internal retries and a 10-second timeout; the chain has a 55-second start budget. This does not reserve provider capacity or guarantee a free model accepts a request.

Gemini-upload URIs and non-image media never go to OpenRouter. Existing compatible inline-image handling is preserved. Free-pool shared upstream rate limits may affect every model. A new key does not buy more shared capacity.

If eligible free routes are exhausted, the result is an honest busy reply, with no new tool calls, provider=none, model=none, busy=true and completed=false. This means the reply did not complete, not that earlier actions in the conversation were rolled back. Never claim a request was completed from a busy result.

## Verification

Authenticated admin-test JSON: {"openrouter_fallback_fixture":true}

The fixture forces a Gemini quota failure only in its own request context. It uses the real configured fallback flag/key, does not override either, sends only a synthetic connectivity prompt and returns attempted models plus actual result. A busy result is ok=false, not a live-failover pass. No global model function/config patch can redirect another user's request.

Local source tests are separate from deployment and live provider proof. All free routes can still be busy; do not describe this as all providers active or fully verified until live results support that.

Sources checked October 17, 2026:
- https://openrouter.ai/api/v1/models
- https://openrouter.ai/docs/guides/routing/model-variants/free
- https://openrouter.ai/docs/guides/routing/provider-selection
