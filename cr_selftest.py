"""Admin-only live self test: runs a message through the real pipeline (real Gemini, real DB)
with a captured sender, so nothing is sent to Telegram. Uses a negative synthetic user id."""
import cr_db as db
import cr_memory as mem
import cr_telegram as tg


def run(body):
    if body.get("diagnostics"):
        users=db.q("SELECT user_id,name,last_seen FROM users WHERE user_id>0 ORDER BY last_seen DESC LIMIT 5")
        events=db.q("SELECT user_id,ts,event,detail FROM audit WHERE event IN ('telegram_reaction','media_processed') ORDER BY ts DESC LIMIT 15")
        return {"ok":True,"users":users,"events":events}
    uid = int(body.get("uid", -4242))
    if uid >= 0:
        return {"ok": False, "error": "selftest only accepts negative synthetic users"}
    texts = body["texts"] if "texts" in body else [body.get("text", "hello")]
    results = []
    if body.get("reset"):
        mem.delete_all(uid)
    for t in texts:
        out = tg.CaptureOut()
        upd = {"message": {"message_id": 1, "chat": {"id": uid}, "from": {"id": uid, "first_name": body.get("name", "SelfTest")}, "text": t}}
        tg.handle_update(upd, out)
        results.append({"in": t, "out": [m["text"] for m in out.sent], "meta": out.meta, "reactions": out.reactions})
    if body.get("media_fixture"):
        import cr_media, base64
        fixture = body["media_fixture"]
        data = base64.b64decode(fixture.get("base64", ""), validate=True)
        if len(data) > cr_media.MAX_BYTES:
            return {"ok": False, "error": "fixture too large"}
        results.append({"media": fixture["mime"], "out": cr_media.analyze(data, fixture["mime"], fixture.get("caption", ""))})
    if body.get("reaction_fixture"):
        from unittest.mock import patch
        out = tg.CaptureOut()
        for text in ("Please build this", "Lets gooo", "thank you", "lol haha", "yes", "/help"):
            upd = {"message":{"message_id":1,"chat":{"id":uid},"from":{"id":uid},"text":text}}
            with patch.object(tg.A, "respond", return_value=("Captured test reply", {})):
                tg.handle_update(upd,out)
        results.append({"reactions":out.reactions,"note":"real transport is captured; no Telegram API calls"})
    if body.get("draft_fixture"):
        import cr_tools
        results.append({"draft": cr_tools.draft_message({"uid":uid}, "Sam", "Ask to reschedule a meeting; new time not chosen yet")})
    if body.get("seed_reminder"):
        from datetime import datetime, timezone, timedelta
        mem.touch_user(uid)
        db.q("INSERT INTO reminders(user_id,chat_id,text,due_at) VALUES(%s,%s,%s,%s)",
            (uid,uid,"Synthetic reminder",datetime.now(timezone.utc)+timedelta(minutes=60)),"none")
    if body.get("proactive_tick"):
        import cr_proactive
        out = tg.CaptureOut()
        # Controlled synthetic clock lets digest windows be verified without touching a real user.
        from unittest.mock import patch
        from datetime import datetime
        import cr_tools
        clock = body.get("synthetic_hour")
        if clock is not None and 0 <= int(clock) <= 23:
            n = cr_tools.now_local(uid).replace(hour=int(clock))
            with patch.object(cr_tools, "now_local", return_value=n):
                sent = cr_proactive.tick(out, only_user=uid)
        else:
            sent = cr_proactive.tick(out, only_user=uid)
        results.append({"proactive_sent": sent, "out": [m["text"] for m in out.sent]})
    if body.get("tick"):
        import cr_sched
        out = tg.CaptureOut()
        ids = cr_sched.tick(out, only_user=uid)
        results.append({"tick_delivered": ids, "sent": [m["text"] for m in out.sent]})
    if body.get("probe") == "reminders":
        rows = db.q("SELECT id,text,status,attempts FROM reminders WHERE user_id=%s ORDER BY id", (uid,))
        results.append({"reminders": [dict(r) for r in rows]})
    if body.get("probe") == "facts":
        results.append({"facts": [dict(key=f["key"], value=f["value"]) for f in mem.facts(uid)]})
    if body.get("work_tick"):
        import cr_work,cr_tools
        from unittest.mock import patch
        cr_work.init();out=tg.CaptureOut()
        n=cr_tools.now_local(uid).replace(hour=12)
        with patch.object(cr_tools,"now_local",return_value=n):
            done=cr_work.tick(out,only_user=uid)
        results.append({"work_tick":done,"out":[m["text"] for m in out.sent]})
    if body.get("work_probe"):
        import cr_work
        cr_work.init()
        rows=db.q("SELECT * FROM work_jobs WHERE user_id=%s ORDER BY id",(uid,))
        results.append({"work_probe":[cr_work.view(r) for r in rows]})
    if body.get("cleanup"):
        mem.delete_all(uid)
    return {"ok": True, "results": results}
