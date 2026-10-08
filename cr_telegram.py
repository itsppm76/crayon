"""Telegram transport (httpx). Long-polling or webhook, both feed handle_update()."""
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx

import cr_agent as A
import cr_config as C
import cr_db as db
import cr_memory as mem
from cr_safety import redact, looks_like_secret

log = logging.getLogger("crayon.tg")
_http = httpx.Client(timeout=httpx.Timeout(45.0, connect=10.0))
_pool = ThreadPoolExecutor(max_workers=6)

HELP = """I'm Crayon. Just talk to me.

What I do:
- remember you across restarts (see /memory)
- set reminders that actually fire ("remind me tomorrow 8am to ...")
- save notes, tell the time, answer questions

Commands:
/memory - what I remember about you
/forget <key> - remove one thing
/delete_my_data - wipe everything I hold on you
/help - this message"""


def api(method, **params):
    r = _http.post(f"https://api.telegram.org/bot{C.TELEGRAM_TOKEN}/{method}", json=params)
    try:
        data = r.json()
    except Exception:
        raise RuntimeError(f"telegram {method}: HTTP {r.status_code}")
    if not data.get("ok"):
        raise RuntimeError(f"telegram {method}: {data.get('description')}")
    return data["result"]


class Out:
    """Real sender. Tests use CaptureOut with the same interface."""
    def send(self, chat_id, text, markup=None):
        text = redact(text) or "(empty)"
        chunks = [text[i:i + 3900] for i in range(0, len(text), 3900)]
        for i, ch in enumerate(chunks):
            params = {"chat_id": chat_id, "text": ch, "disable_web_page_preview": True}
            if markup and i == len(chunks) - 1:
                params["reply_markup"] = markup
            api("sendMessage", **params)

    def typing(self, chat_id):
        try:
            api("sendChatAction", chat_id=chat_id, action="typing")
        except Exception:
            pass

    def delete(self, chat_id, message_id):
        try:
            api("deleteMessage", chat_id=chat_id, message_id=message_id)
            return True
        except Exception:
            return False


class CaptureOut:
    def __init__(self):
        self.sent, self.meta = [], {}

    def send(self, chat_id, text, markup=None):
        self.sent.append({"text": redact(text), "markup": bool(markup)})

    def typing(self, chat_id):
        pass

    def delete(self, chat_id, message_id):
        return True


def _over_cap(uid):
    r = db.q("SELECT count(*) AS n FROM messages WHERE user_id=%s AND role='user' AND ts > now() - interval '24 hours'", (uid,), "one")
    return r["n"] >= C.DAILY_MESSAGE_CAP


def handle_update(upd, out=None):
    out = out or Out()
    try:
        if "callback_query" in upd:
            return handle_callback(upd["callback_query"], out)
        msg = upd.get("message")
        if not msg:
            return
        chat_id = msg["chat"]["id"]
        uid = msg["from"]["id"]
        name = (msg["from"].get("first_name") or "").strip()
        text = msg.get("text")
        if not text:
            out.send(chat_id, "I can only read text messages for now. Type it out and I'll help.")
            return
        with mem.user_lock(uid):
            _handle_text(uid, chat_id, name, text, msg.get("message_id"), out)
    except Exception as e:
        log.exception("handle_update failed")
        try:
            out.send(upd.get("message", {}).get("chat", {}).get("id"), "Something went wrong on my side and I couldn't finish that. Nothing was changed. Try again in a moment.")
        except Exception:
            pass


def _handle_text(uid, chat_id, name, text, message_id, out):
    if looks_like_secret(text):
        out.delete(chat_id, message_id)
        out.send(chat_id, "That looked like a password or key, so I deleted your message and did not save it. Don't paste secrets here. If it was real, rotate it.")
        db.audit(uid, "secret_blocked")
        return
    cmd, _, arg = text.partition(" ")
    cmd = cmd.split("@")[0].lower()
    arg = arg.strip()
    if cmd == "/start":
        mem.touch_user(uid, name)
        out.send(chat_id, f"Hi{' ' + name if name else ''}, I'm Crayon. I remember what matters about you now, even after restarts. Say hi, or try /help.")
    elif cmd == "/help":
        out.send(chat_id, HELP)
    elif cmd == "/memory":
        out.send(chat_id, mem.render_memory(uid))
    elif cmd == "/forget":
        if not arg:
            out.send(chat_id, "Which one? Use /memory to see keys, then /forget <key>.")
        else:
            ok = mem.forget(uid, arg)
            out.send(chat_id, f"Removed '{arg}'." if ok else f"I tried to remove '{arg}' but it's still there. Not confirmed.")
    elif cmd == "/delete_my_data":
        if arg.lower() == "confirm":
            ok = mem.delete_all(uid)
            out.send(chat_id, "Everything I held on you is deleted (checked: nothing left)." if ok else "I tried to wipe your data but some rows remain. Not fully deleted.")
        else:
            out.send(chat_id, "This permanently deletes your memory, notes, reminders and chat history. To go ahead, send: /delete_my_data confirm")
    elif text.startswith("/"):
        out.send(chat_id, "I don't know that command. /help lists what I understand.")
    else:
        if _over_cap(uid):
            out.send(chat_id, "You've hit today's message limit for the free tier. Try again tomorrow.")
            return
        out.typing(chat_id)
        reply, meta = A.respond(uid, chat_id, text, name)
        if hasattr(out, "meta"):
            out.meta = meta
        out.send(chat_id, reply)


def handle_callback(cb, out):  # filled in by the safety milestone
    try:
        api("answerCallbackQuery", callback_query_id=cb["id"])
    except Exception:
        pass


def set_commands():
    try:
        api("setMyCommands", commands=[
            {"command": "memory", "description": "What I remember about you"},
            {"command": "forget", "description": "Remove one remembered thing"},
            {"command": "delete_my_data", "description": "Wipe all my data"},
            {"command": "help", "description": "What I can do"}])
    except Exception as e:
        log.warning("setMyCommands failed: %s", redact(str(e)))


def poll_forever(stop=None):
    offset = 0
    try:
        offset = int(db.kv_get("tg_offset", 0) or 0)
    except Exception:
        pass
    try:
        api("deleteWebhook", drop_pending_updates=False)
    except Exception as e:
        log.warning("deleteWebhook: %s", redact(str(e)))
    log.info("polling started at offset %s", offset)
    while not (stop and stop.is_set()):
        try:
            r = _http.post(f"https://api.telegram.org/bot{C.TELEGRAM_TOKEN}/getUpdates",
                           json={"offset": offset, "timeout": 25, "allowed_updates": ["message", "callback_query"]}, timeout=40)
            data = r.json()
            if not data.get("ok"):
                if r.status_code == 409:
                    time.sleep(6)  # another instance polling during a deploy
                else:
                    log.warning("getUpdates: %s", redact(str(data.get("description"))))
                    time.sleep(3)
                continue
            for upd in data["result"]:
                offset = upd["update_id"] + 1
                _pool.submit(handle_update, upd)
            if data["result"]:
                try:
                    db.kv_set("tg_offset", offset)
                except Exception:
                    pass
        except Exception as e:
            log.warning("poll error: %s", redact(f"{type(e).__name__}: {e}")[:200])
            time.sleep(3)
