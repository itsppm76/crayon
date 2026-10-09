import hashlib
import hmac
import json

import cr_telegram as T
import cr_whatsapp as W

OWNER = "918777566396"


def env(monkeypatch):
    for k, v in {"WHATSAPP_ACCESS_TOKEN": "t", "WHATSAPP_PHONE_NUMBER_ID": "123", "WHATSAPP_APP_SECRET": "secret",
                 "WHATSAPP_VERIFY_TOKEN": "vt", "CRAYON_OWNER_WA_ID": OWNER}.items():
        monkeypatch.setenv(k, v)
    W._seen.clear()


def payload(sender, mid, text=None, button=None, typ=None):
    m = {"id": mid, "from": sender}
    if button:
        m.update(type="interactive", interactive={"button_reply": {"id": button}})
    elif typ:
        m["type"] = typ
    else:
        m.update(type="text", text={"body": text})
    return {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": {
        "contacts": [{"wa_id": sender, "profile": {"name": "Uttiya"}}], "messages": [m]}}]}]}


def sign(p, secret="secret"):
    raw = json.dumps(p).encode()
    return raw, "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()


class Sync:
    def submit(self, fn, *a):
        fn(*a)


def test_handshake(monkeypatch):
    env(monkeypatch)
    assert W.verify_challenge({"hub.mode": "subscribe", "hub.verify_token": "vt", "hub.challenge": "42"}) == "42"
    assert W.verify_challenge({"hub.mode": "subscribe", "hub.verify_token": "bad", "hub.challenge": "42"}) is None


def test_bad_signature_and_disabled(monkeypatch):
    env(monkeypatch)
    monkeypatch.setattr(W, "_pool", Sync())
    monkeypatch.setattr(W, "process", lambda *a: (_ for _ in ()).throw(AssertionError("processed")))
    raw, _ = sign(payload(OWNER, "m1", "hi"))
    assert W.handle_webhook(raw, "sha256=00") == 403
    assert W.handle_webhook(raw, None) == 403
    monkeypatch.delenv("WHATSAPP_APP_SECRET")
    assert W.handle_webhook(raw, "sha256=00") == 404


def test_owner_only_and_dedupe(monkeypatch):
    env(monkeypatch)
    monkeypatch.setattr(W, "_pool", Sync())
    calls = []
    monkeypatch.setattr(W, "process", lambda kind, value, uid, name, out=None: calls.append((kind, value, uid, name)))
    for p in (payload("919000000000", "m0", "hi"), payload(OWNER, "m1", "hi"), payload(OWNER, "m1", "hi")):
        raw, sig = sign(p)
        assert W.handle_webhook(raw, sig) == 200
    assert calls == [("text", "hi", int(OWNER), "Uttiya")]


def test_text_becomes_private_update(monkeypatch):
    seen = {}
    monkeypatch.setattr(T, "handle_update", lambda upd, out=None: seen.update(upd=upd, out=out))
    W.process("text", "remind me", int(OWNER), "Uttiya")
    m = seen["upd"]["message"]
    assert m["chat"] == {"id": int(OWNER), "type": "private"} and m["from"]["id"] == int(OWNER) and m["text"] == "remind me"
    assert isinstance(seen["out"], W.WhatsAppOut)


def test_button_reply_becomes_callback(monkeypatch):
    seen = {}
    monkeypatch.setattr(T, "handle_callback", lambda cb, out: seen.update(cb=cb))
    W.process("button", "email_send:1:abc", int(OWNER), "")
    assert seen["cb"]["data"] == "email_send:1:abc" and seen["cb"]["from"]["id"] == int(OWNER) == seen["cb"]["message"]["chat"]["id"]


def test_non_text_gets_text_only_reply():
    class Cap:
        def __init__(self): self.sent = []
        def send(self, c, t, markup=None): self.sent.append(t)
    c = Cap()
    W.process("other", "", int(OWNER), "", c)
    assert "Text only" in c.sent[0]


def test_out_sends_buttons_and_list(monkeypatch):
    posts = []
    monkeypatch.setattr(W, "_post", lambda body: posts.append(body) or "id")
    o = W.WhatsAppOut()
    o.send(OWNER, "Review", {"inline_keyboard": [[{"text": "Send", "callback_data": "email_send:1:a"}, {"text": "Cancel", "callback_data": "email_cancel:1"}]]})
    assert posts[0]["type"] == "text" and posts[1]["interactive"]["type"] == "button"
    assert [b["reply"]["id"] for b in posts[1]["interactive"]["action"]["buttons"]] == ["email_send:1:a", "email_cancel:1"]
    posts.clear()
    five = {"inline_keyboard": [[{"text": "B%d" % i, "callback_data": "work:show:%d" % i}] for i in range(1, 6)]}
    o.send(OWNER, "Job", five)
    assert posts[1]["interactive"]["type"] == "list" and len(posts[1]["interactive"]["action"]["sections"][0]["rows"]) == 5
    posts.clear()
    o.send(OWNER, "x" * 8000)
    assert len(posts) == 3 and all(p["type"] == "text" for p in posts)
    assert o.react(OWNER, 1, "👍") is False and o.delete(OWNER, 1) is False


def test_telegram_out_routes_whatsapp_chat_ids(monkeypatch):
    env(monkeypatch)
    sent = []
    monkeypatch.setattr(W, "_post", lambda body: sent.append(body) or "id")
    monkeypatch.setattr(T, "api", lambda *a, **k: (_ for _ in ()).throw(AssertionError("telegram used")))
    T.Out().send(int(OWNER), "Reminder: call Mum")
    assert sent[0]["to"] == OWNER and sent[0]["text"]["body"] == "Reminder: call Mum"
    assert W.owns(int(OWNER)) and not W.owns(12345) and not W.owns(None)
