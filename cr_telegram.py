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
from cr_safety import redact, looks_like_secret, clean_text

log = logging.getLogger("crayon.tg")
_http = httpx.Client(timeout=httpx.Timeout(45.0, connect=10.0))
_pool = ThreadPoolExecutor(max_workers=6)

HELP = """I'm Crayon. Just talk to me.

What I do:
- remember you across restarts (see /memory)
- set reminders that actually fire ("remind me tomorrow 8am to ...")
- draft messages for review (never sends to other people)
- save notes, tell the time, answer questions
- accept files up to 20 MB, read common documents/photos/audio/video
- inspect ZIP/TAR listings; explain formats I cannot decode

Commands:
/goal <goal> - plan and execute bounded multi-step work
/memory_review - duplicates and reviewable preference suggestions
/proactive on|off - opt-in daily task/reminder check-in
/digest morning|evening|both|off - opt-in daily digests
/digest_now - task/reminder summary now
/quiet_hours 21 9 - silence check-ins and digests at night
/connect_google - connect your own Google (testing mode)
/google_status, /disconnect_google - connection controls
/gmail <search>, /gmail_read <ID>, /calendar - direct reads
/email_draft, /email_send, /email_cancel - reviewed email only
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
        text = clean_text(text) or "(empty)"
        chunks = [text[i:i + 3900] for i in range(0, len(text), 3900)]
        for i, ch in enumerate(chunks):
            params = {"chat_id": chat_id, "text": ch, "disable_web_page_preview": True}
            if markup and i == len(chunks) - 1:
                params["reply_markup"] = markup
            api("sendMessage", **params)

    def react(self, chat_id, message_id, emoji):
        try:
            api("setMessageReaction", chat_id=chat_id, message_id=message_id,
                reaction=[{"type":"emoji", "emoji":emoji}], is_big=False)
            return True
        except Exception as e:
            log.warning("reaction failed: %s", redact(str(e))[:180])
            return False

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
        self.sent, self.meta, self.reactions = [], {}, []

    def send(self, chat_id, text, markup=None):
        self.sent.append({"text": clean_text(text), "markup": bool(markup)})

    def react(self, chat_id, message_id, emoji):
        self.reactions.append({"emoji":emoji,"message_id":message_id})
        return True

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
        if msg["chat"].get("type") in ("group","supergroup"):
            import cr_group
            if not cr_group.mentioned(msg):return
            finished=threading.Event()
            def group_progress():
                for delay,line in ((12,"On it. Give me a moment."),(25,"Still working on it. I'll send the answer when it's ready.")):
                    if finished.wait(delay):return
                    try:out.send(chat_id,line)
                    except Exception:pass
            threading.Thread(target=group_progress,daemon=True).start()
            try:
                out.typing(chat_id)
                out.send(chat_id,cr_group.answer(msg))
            finally:finished.set()
            return
        if uid > 0:
            db.kv_set("tg_latest_"+str(uid), {"chat_id":chat_id,"message_id":msg.get("message_id"),
                "media":any(msg.get(k) for k in ("photo","voice","audio","document","video","video_note","animation","sticker"))})
        text = msg.get("text")
        if text and text.startswith(("/email_send", "/email_draft", "/connect_google")) and (msg.get("forward_origin") or msg.get("forward_from") or msg.get("via_bot")):
            out.send(chat_id, "Google actions need a direct command from you, not forwarded content.")
            return
        if any(msg.get(k) for k in ("photo","voice","audio","document","video","video_note","animation","sticker")) or not text:
            with mem.user_lock(uid):
                _handle_media(uid, chat_id, name, msg, out)
            return
        with mem.user_lock(uid):
            finished=threading.Event()
            def progress():
                for delay,line in ((12,"On it. Give me a moment."),(25,"Still working on it. I'll send the answer when it's ready."),(35,"This is taking longer than usual. I'm still checking.")):
                    if finished.wait(delay):return
                    try:out.send(chat_id,line)
                    except Exception:pass
            threading.Thread(target=progress,daemon=True).start()
            try:
                _handle_text(uid, chat_id, name, text, msg.get("message_id"), out)
            finally:finished.set()
    except Exception as e:
        log.exception("handle_update failed")
        try:
            out.send(upd.get("message", {}).get("chat", {}).get("id"), "Something went wrong on my side and I couldn't finish that. Nothing was changed. Try again in a moment.")
        except Exception:
            pass


def msg_private_invalid(uid):
    return uid <= 0


def _handle_text(uid, chat_id, name, text, message_id, out):
    if looks_like_secret(text):
        out.delete(chat_id, message_id)
        out.send(chat_id, "That looked like a password or key, so I deleted your message and did not save it. Don't paste secrets here. If it was real, rotate it.")
        db.audit(uid, "secret_blocked")
        return
    import cr_reactions
    emoji = cr_reactions.choose(text)
    if emoji and message_id and hasattr(out, "react"):
        reaction_ok = out.react(chat_id, message_id, emoji)
        db.audit(uid,"telegram_reaction",f"message_id={message_id} emoji={emoji} accepted={reaction_ok}")
    fields = text.split(None,1)
    if not fields:return
    cmd, arg = fields[0], fields[1] if len(fields)>1 else ""
    cmd = cmd.split("@")[0].lower()
    arg = arg.strip()
    if cmd == "/start":
        mem.touch_user(uid, name)
        out.send(chat_id, f"Hi{' ' + name if name else ''}, I'm Crayon. I remember what matters about you now, even after restarts. Say hi, or try /help.")
    elif cmd == "/help":
        out.send(chat_id, HELP)
    elif cmd == "/goal":
        if not arg:
            out.send(chat_id, "Use /goal followed by a concrete research or calculation goal.")
        elif _over_cap(uid):
            out.send(chat_id, "Today's free-tier message limit is reached.")
        else:
            out.typing(chat_id)
            reply, meta = A.respond(uid, chat_id, arg, name, goal_mode=True)
            if hasattr(out, "meta"):
                out.meta = meta
            out.send(chat_id, reply)
    elif cmd in ("/connect_google", "/disconnect_google", "/google_status", "/gmail", "/gmail_read", "/calendar", "/email_draft", "/email_send", "/email_cancel"):
        import cr_google as G
        if chat_id != uid or msg_private_invalid(uid):
            out.send(chat_id, "Google commands only work in your private chat with Crayon.")
            return
        try:
            if cmd != "/disconnect_google" and not G.configured():
                raise G.GoogleError("Google setup is not active yet")
            if cmd == "/connect_google":
                out.send(chat_id, "Google testing mode: only named test users can connect; reconnect after 7 days. Read the privacy policy before connecting: " + C.PUBLIC_URL + "/privacy\nMailbox/calendar results are shown in this private Telegram chat, not sent to the AI model or permanent memory. Tokens are encrypted. Sending always needs an exact draft confirmation.\nConnect your own account: " + G.begin(uid))
            elif cmd == "/disconnect_google":
                r=G.disconnect(uid)
                out.send(chat_id, "Stored Google credentials and pending drafts removed. " + ("Google revocation confirmed." if r["revoked"] else "Google revocation was not confirmed; remove Crayon access in your Google account too."))
            elif cmd == "/google_status":
                r=G.status(uid)
                out.send(chat_id, "Connected Google account: " + r["email"] if r else "No Google account connected.")
            elif cmd == "/gmail":
                out.send(chat_id,G.inbox(uid,arg))
            elif cmd == "/gmail_read":
                out.send(chat_id,G.read_message(uid,arg))
            elif cmd == "/calendar":
                out.send(chat_id,G.calendar(uid))
            elif cmd == "/email_draft":
                out.send(chat_id,G.make_draft(uid,arg))
            elif cmd == "/email_send":
                bits=arg.split()
                if len(bits)!=2:raise G.GoogleError("Use the exact /email_send command shown beneath your draft")
                out.send(chat_id,G.send_draft(uid,*bits))
            elif cmd == "/email_cancel":
                out.send(chat_id,G.cancel_draft(uid,arg))
        except G.GoogleError as e:
            out.send(chat_id,str(e))
        except Exception:
            out.send(chat_id,"Google request failed. No action is confirmed. Try reconnecting if access expired.")
    elif cmd == "/memory_review":
        import json
        mem.touch_user(uid, name)
        review = mem.review_memory(uid)
        out.send(chat_id, "Memory review (no facts changed):\n" + json.dumps(review, ensure_ascii=False, indent=2))
        if hasattr(out, "meta"):
            out.meta = {"memory_review": review}
    elif cmd in ("/proactive", "/digest", "/quiet_hours"):
        import cr_proactive as P
        if cmd == "/quiet_hours":
            try:
                start, end = [int(x) for x in arg.split()]
                if not (0 <= start <= 23 and 0 <= end <= 23):
                    raise ValueError()
                P.set_option(uid, chat_id, "quiet_start", start)
                ok = P.set_option(uid, chat_id, "quiet_end", end)
                out.send(chat_id, f"Quiet hours: {start}:00 to {end}:00 in your timezone." if ok else "Couldn't save quiet hours.")
            except Exception:
                out.send(chat_id, "Use /quiet_hours <start hour> <end hour>, e.g. /quiet_hours 21 9.")
        else:
            key = "proactive" if cmd == "/proactive" else "digest"
            allowed = ("on", "off") if key == "proactive" else ("morning", "evening", "both", "off")
            if arg not in allowed:
                out.send(chat_id, "Use " + cmd + " " + "|".join(allowed) + ". Currently: " + str(P.settings(uid)[key]))
            else:
                value = (arg == "on") if key == "proactive" else arg
                ok = P.set_option(uid, chat_id, key, value)
                out.send(chat_id, cmd[1:] + " is " + arg + ". Quiet hours apply; free-host timing is best-effort." if ok else "Couldn't save that setting.")
    elif cmd == "/digest_now":
        import cr_proactive as P
        mem.touch_user(uid, name)
        out.send(chat_id, P.digest_text(uid))
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


def _handle_media(uid, chat_id, name, msg, out):
    import cr_media
    item, mime = None, ""
    if msg.get("photo"):
        item, mime = msg["photo"][-1], "image/jpeg"
    elif msg.get("voice"):
        item, mime = msg["voice"], "audio/ogg"
    elif msg.get("audio"):
        item = msg["audio"]
        mime = item.get("mime_type", "audio/mpeg")
    elif msg.get("document"):
        item = msg["document"]
        mime = item.get("mime_type", "")
    else:
        for kind in ("video", "video_note", "animation", "sticker"):
            if msg.get(kind):
                item = msg[kind]
                mime = item.get("mime_type") or ("video/webm" if item.get("is_video") else "application/x-tgsticker" if item.get("is_animated") else "image/webp" if kind=="sticker" else "video/mp4")
                break
    if not item:
        out.send(chat_id, "I received an attachment type I cannot read yet. Try sending it as a document.")
        return
    caption = msg.get("caption", "")
    if looks_like_secret(caption):
        out.delete(chat_id, msg.get("message_id"))
        out.send(chat_id, "The caption appears to contain a secret. I did not process or save it.")
        return
    finished = threading.Event()
    def progress(text):
        try:
            out.send(chat_id, text)
        except Exception:
            pass
    def keep_updated():
        for message in ("Still reading it. Larger files can take a little longer.", "Still processing with the media provider. I will tell you if it fails."):
            if finished.wait(25):
                return
            progress(message)
    try:
        mem.touch_user(uid, name)
        if _over_cap(uid):
            out.send(chat_id, "Today's free-tier message limit is reached.")
            return
        if item.get("file_size", 0) > cr_media.MAX_BYTES:
            raise ValueError("Telegram bot downloads are limited to 20 MB. Send a smaller file or split it.")
        if msg.get("message_id") and hasattr(out, "react"):
            accepted=out.react(chat_id,msg["message_id"],"👀")
            db.audit(uid,"telegram_reaction",f"message_id={msg['message_id']} emoji=👀 accepted={accepted}")
        progress("Big file, give me a moment to read it." if item.get("file_size", 0)>4_000_000 else "Got it, reading your file now.")
        threading.Thread(target=keep_updated, daemon=True).start()
        out.typing(chat_id)
        f = api("getFile", file_id=item["file_id"])
        path = f.get("file_path", "")
        if not path or ".." in path or path.startswith("/"):
            raise ValueError("Could not get the upload safely.")
        if f.get("file_size", 0) > cr_media.MAX_BYTES:
            raise ValueError("Upload exceeds the 20 MB download limit.")
        data = bytearray()
        with _http.stream("GET", f"https://api.telegram.org/file/bot{C.TELEGRAM_TOKEN}/{path}") as r:
            r.raise_for_status()
            for chunk in r.iter_bytes():
                data.extend(chunk)
                if len(data) > cr_media.MAX_BYTES:
                    raise ValueError("Upload exceeds the 20 MB download limit.")
        reply = cr_media.analyze(bytes(data), mime, caption, item.get("file_name", ""), progress=progress)
        finished.set()
        db.audit(uid,"media_processed", f"mime={mime} bytes={len(data)}")
        mem.add_message(uid, "user", "[User sent media: " + mime + "] " + redact(caption))
        mem.add_message(uid, "assistant", "[Media analysis summary; raw file not retained] " + clean_text(reply)[:3000])
        if hasattr(out, "meta"):
            out.meta = {"media": mime, "bytes": len(data), "verified": bool(reply)}
        out.send(chat_id, reply or "I couldn't read that clearly.")
    except Exception as e:
        finished.set()
        log.warning("media handling failed: %s",type(e).__name__)
        reason = str(e) if isinstance(e, ValueError) else "The download or media provider failed. Try a smaller file or retry shortly."
        out.send(chat_id, "I couldn't read that upload: " + redact(reason)[:200])
    finally:
        finished.set()
