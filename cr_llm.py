"""Gemini REST client (free tier). Native function calling, retries, model fallback."""
import json
import logging
import time

import httpx

import cr_config as C
from cr_safety import redact

log = logging.getLogger("crayon.llm")
_client = httpx.Client(timeout=httpx.Timeout(60.0, connect=10.0))
_BASE = "https://generativelanguage.googleapis.com/v1beta/models/"


class LLMError(Exception):
    def __init__(self, kind, detail=""):
        super().__init__(f"{kind}: {detail}")
        self.kind = kind  # quota | auth | unavailable | bad_request | empty
        self.detail = detail


def _post(model, body):
    r = _client.post(_BASE + model + ":generateContent", headers={"x-goog-api-key": C.GEMINI_KEY}, json=body)
    return r


def generate(contents, system="", tools=None, json_mode=False, temperature=0.6, max_tokens=1500,
             models=None, thinking_budget=None):
    """Returns dict: {text, calls:[{name,args}], raw_parts, model}. Raises LLMError."""
    if not C.GEMINI_KEY:
        raise LLMError("auth", "no GEMINI_API_KEY")
    body = {"contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}}
    if thinking_budget is not None:
        body["generationConfig"]["thinkingConfig"] = {"thinkingBudget": thinking_budget}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if tools:
        body["tools"] = tools
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"
    errs = []
    for model in (models or [C.GEMINI_MODEL] + C.GEMINI_FALLBACKS):
        for attempt in range(2):
            try:
                r = _post(model, body)
            except httpx.HTTPError as e:
                errs.append(f"{model}:net:{type(e).__name__}")
                time.sleep(1.0)
                continue
            if r.status_code == 200:
                data = r.json()
                cands = data.get("candidates") or []
                if not cands or not cands[0].get("content", {}).get("parts"):
                    reason = (cands[0].get("finishReason") if cands else (data.get("promptFeedback") or {}).get("blockReason"))
                    errs.append(f"{model}:empty:{reason}")
                    break
                parts = cands[0]["content"]["parts"]
                text = "".join(p.get("text", "") for p in parts if "text" in p and not p.get("thought"))
                calls = [{"name": p["functionCall"]["name"], "args": p["functionCall"].get("args", {}) or {}}
                         for p in parts if "functionCall" in p]
                return {"text": text.strip(), "calls": calls, "parts": parts, "model": model, "raw": data}
            if r.status_code == 429:
                errs.append(f"{model}:429")
                time.sleep(1.5 if attempt == 0 else 0)
                continue
            if r.status_code in (401, 403):
                raise LLMError("auth", f"HTTP {r.status_code}")
            if r.status_code == 404:
                errs.append(f"{model}:404")
                break
            if r.status_code == 400:
                raise LLMError("bad_request", redact(r.text[:300]))
            errs.append(f"{model}:{r.status_code}")
            time.sleep(1.0)
    kind = "quota" if any(e.endswith(":429") for e in errs) else "unavailable"
    raise LLMError(kind, ", ".join(errs))


def user(text):
    return {"role": "user", "parts": [{"text": text}]}


def model_msg(text):
    return {"role": "model", "parts": [{"text": text}]}


def ask_json(prompt, system="", default=None, temperature=0.2, max_tokens=800):
    """One-shot structured call. Returns parsed JSON or default on any failure."""
    try:
        out = generate([user(prompt)], system=system, json_mode=True, temperature=temperature,
                       max_tokens=max_tokens, thinking_budget=0)
        t = out["text"].strip()
        if t.startswith("```"):
            t = t.strip("`")
            t = t[t.find("\n") + 1:] if "\n" in t else t
        return json.loads(t)
    except Exception as e:
        log.warning("ask_json failed: %s", redact(str(e))[:200])
        return default
