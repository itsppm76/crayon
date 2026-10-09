"""WhatsApp Cloud API transport. Same Crayon brain as Telegram.

Meta POSTs a signed webhook to /whatsapp/webhook (served by main.py). We verify the
X-Hub-Signature-256 header, accept only allow-listed senders, skip repeats, turn the
message into a Telegram-shaped update and call cr_telegram.handle_update with
WhatsAppOut, which sends replies through the Graph API.

A WhatsApp user is a separate Crayon user: uid = their number in digits (for example
918777566396). Their memory, notes and reminders are separate from any Telegram account.
Free-form messages only work within 24 hours of the person's last message to the number.
Tokens and the app secret are never logged.
"""
import hashlib
import hmac
import logging
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

import httpx

import cr_config as C
from cr_safety import clean_text, redact

log = logging.getLogger("crayon.wa")
_http = httpx.Client(timeout=httpx.Timeout(30.0, connect=10.0))
_pool = ThreadPoolExecutor(max_workers=4)
_seen = OrderedDict()
_lock = threading.Lock()
TEXT_LIMIT = 3500  # WhatsApp allows 4096


def allowed_ids():
    raw = C.env("WHATSAPP_ALLOWED_IDS") or C.env("CRAYON_OWNER_WA_ID")
    return {"".join(ch for ch in x if ch.isdigit()) for x in raw.split(",") if any(ch.isdigit() for ch in x)}


def enabled():
    return bool(C.env("WHATSAPP_ACCESS_TOKEN") and C.env("WHATSAPP_PHONE_NUMBER_ID") and C.env("WHATSAPP_APP_SECRET")
                and C.env("WHATSAPP_VERIFY_TOKEN") and allowed_ids())


def owns(chat_id):
    """True when a chat id belongs to a WhatsApp user, so Telegram-side senders
    (reminders, digests) route to WhatsApp instead."""
    try:
        return str(int(chat_id)) in allowed_ids()
    except (TypeError, ValueError):
        return False


def _api_url(path):
    return f"https://graph.facebook.com/{C.env('WHATSAPP_GRAPH_VERSION', 'v25.0')}/{C.env('WHATSAPP_PHONE_NUMBER_ID')}/{path}"


def _headers():
    return {"Authorization": "Bearer " + C.env("WHATSAPP_ACCESS_TOKEN")}


def _post(body):
    try:
        r = _http.post(_api_url("messages"), headers=_headers(), json=body)
    except httpx.HTTPError:
        log.warning("whatsapp send failed (network)")
        return None
    if r.status_code >= 400:
        # Status code only; the body can echo account details.
        log.warning("whatsapp send failed: HTTP %s%s", r.status_code,
                    " (token expired or invalid: generate a new WHATSAPP_ACCESS_TOKEN)" if r.status_code == 401 else "")
        return None
    try:
        return r.json()["messages"][0]["id"]
    except Exception:
        return "sent"


def verify_signature(app_secret, raw_body, header):
    if not app_secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header[7:])


def verify_challenge(args):
    """GET handshake. args is a dict of single values. Returns the challenge or None."""
    tok = C.env("WHATSAPP_VERIFY_TOKEN")
    if args.get("hub.mode") == "subscribe" and tok and hmac.compare_digest(args.get("hub.verify_token", ""), tok):
        return args.get("hub.challenge", "")
    return None


def extract_messages(payload):
    """Yield (message_id, sender, kind, value, profile_name). kind: text, button, other."""
    if payload.get("object") != "whatsapp_business_account":
        return
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            names = {c.get("wa_id"): c.get("profile", {}).get("name", "") for c in value.get("contacts", [])}
            for m in value.get("messages", []):
                mid, sender, typ = m.get("id"), m.get("from"), m.get("type")
                if not mid or not sender:
                    continue
                name = names.get(sender, "")
                if typ == "text":
                    yield mid, sender, "text", m.get("text", {}).get("body", ""), name
                elif typ == "interactive":
                    i = m.get("interactive", {})
                    pick = i.get("button_reply") or i.get("list_reply") or {}
                    yield mid, sender, "button", pick.get("id", ""), name
                else:
                    yield mid, sender, "other", "", name


def _buttons_from_markup(markup):
    """Telegram inline_keyboard -> [(callback_data, title)]. Reply keyboards are ignored."""
    out = []
    for row in (markup or {}).get("inline_keyboard", []) if isinstance(markup, dict) else []:
        for b in row:
            cd, title = b.get("callback_data"), b.get("text")
            if cd and title and len(cd) <= 200:
                out.append((cd, title))
    return out[:10]


class WhatsAppOut:
    """Same interface as cr_telegram.Out."""

    def send(self, chat_id, text, markup=None):
        to = str(chat_id)
        text = clean_text(text) or "(empty)"
        for i in range(0, len(text), TEXT_LIMIT):
            _post({"messaging_product": "whatsapp", "to": to, "type": "text",
                   "text": {"body": text[i:i + TEXT_LIMIT], "preview_url": False}})
        buttons = _buttons_from_markup(markup)
        if not buttons:
            return
        if len(buttons) <= 3:
            _post({"messaging_product": "whatsapp", "to": to, "type": "interactive",
                   "interactive": {"type": "button", "body": {"text": "Choose an option:"},
                                   "action": {"buttons": [{"type": "reply", "reply": {"id": cd, "title": t[:20]}}
                                                          for cd, t in buttons]}}})
        else:
            _post({"messaging_product": "whatsapp", "to": to, "type": "interactive",
                   "interactive": {"type": "list", "body": {"text": "Choose an option:"},
                                   "action": {"button": "Options", "sections": [{"title": "Options", "rows": [
                                       {"id": cd, "title": t[:24]} for cd, t in buttons]}]}}})

    def artifact(self, chat_id, item):
        if len(item["data"]) > 2000000:
            raise ValueError("attachment too large")
        mime = item["mime"]
        try:
            r = _http.post(_api_url("media"), headers=_headers(), data={"messaging_product": "whatsapp", "type": mime},
                           files={"file": (item["filename"], item["data"], mime)})
            media_id = r.json()["id"] if r.status_code < 400 else None
        except Exception:
            media_id = None
        if not media_id:
            raise RuntimeError("WhatsApp attachment not confirmed")
        if mime == "image/png" and len(item["data"]) <= 5000000:
            body = {"type": "image", "image": {"id": media_id}}
        else:
            body = {"type": "document", "document": {"id": media_id, "filename": item["filename"]}}
        mid = _post({"messaging_product": "whatsapp", "to": str(chat_id), **body})
        if not mid:
            raise RuntimeError("WhatsApp attachment not confirmed")
        return mid

    def react(self, chat_id, message_id, emoji):
        return False  # no reactions on WhatsApp (never claim one was sent)

    def typing(self, chat_id):
        pass

    def delete(self, chat_id, message_id):
        return False  # WhatsApp cannot delete a user's message


def _seen_before(mid):
    with _lock:
        if mid in _seen:
            return True
        _seen[mid] = True
        while len(_seen) > 1000:
            _seen.popitem(last=False)
        return False


def process(kind, value, uid, name, out=None):
    import cr_telegram as T
    out = out or WhatsAppOut()
    if kind == "other":
        out.send(uid, "Text only on WhatsApp for now. Send it as text and I'll help.")
    elif kind == "button":
        T.handle_callback({"id": "wa", "data": value, "from": {"id": uid}, "message": {"chat": {"id": uid}}}, out)
    else:
        T.handle_update({"message": {"chat": {"id": uid, "type": "private"},
                                     "from": {"id": uid, "first_name": name}, "text": value}}, out)


def handle_webhook(raw_body, signature):
    """Called from main.py POST. Returns an HTTP status code."""
    if not enabled():
        return 404
    if not verify_signature(C.env("WHATSAPP_APP_SECRET"), raw_body, signature):
        return 403
    import json
    try:
        payload = json.loads(raw_body or b"{}")
    except Exception:
        return 200
    allow = allowed_ids()
    for mid, sender, kind, value, name in extract_messages(payload):
        if sender not in allow or _seen_before(mid):
            continue  # not an allowed sender: ignored silently
        _pool.submit(_safe_process, kind, value, int(sender), name)
    return 200


def _safe_process(kind, value, uid, name):
    try:
        process(kind, value, uid, name)
    except Exception as e:
        log.warning("whatsapp handler error: %s", redact(f"{type(e).__name__}: {e}")[:200])
