"""Admin-only live self test: runs a message through the real pipeline (real Gemini, real DB)
with a captured sender, so nothing is sent to Telegram. Uses a negative synthetic user id."""
import cr_db as db
import cr_memory as mem
import cr_telegram as tg


def run(body):
    uid = int(body.get("uid", -4242))
    texts = body.get("texts") or [body.get("text", "hello")]
    results = []
    if body.get("reset"):
        mem.delete_all(uid)
    for t in texts:
        out = tg.CaptureOut()
        upd = {"message": {"message_id": 1, "chat": {"id": uid}, "from": {"id": uid, "first_name": body.get("name", "SelfTest")}, "text": t}}
        tg.handle_update(upd, out)
        results.append({"in": t, "out": [m["text"] for m in out.sent], "meta": out.meta})
    if body.get("probe") == "facts":
        results.append({"facts": [dict(key=f["key"], value=f["value"]) for f in mem.facts(uid)]})
    if body.get("cleanup"):
        mem.delete_all(uid)
    return {"ok": True, "results": results}
