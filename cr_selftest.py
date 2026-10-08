"""Admin-only live self test: runs a message through the real pipeline (real Gemini, real DB)
with a captured sender, so nothing is sent to Telegram. Uses a negative synthetic user id."""
import cr_db as db
import cr_memory as mem
import cr_telegram as tg


def run(body):
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
        results.append({"in": t, "out": [m["text"] for m in out.sent], "meta": out.meta})
    if body.get("media_fixture"):
        import cr_media, base64
        fixture = body["media_fixture"]
        data = base64.b64decode(fixture.get("base64", ""), validate=True)
        if len(data) > cr_media.MAX_BYTES:
            return {"ok": False, "error": "fixture too large"}
        results.append({"media": fixture["mime"], "out": cr_media.analyze(data, fixture["mime"], fixture.get("caption", ""))})
    if body.get("proactive_tick"):
        import cr_proactive
        out = tg.CaptureOut()
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
    if body.get("cleanup"):
        mem.delete_all(uid)
    return {"ok": True, "results": results}
