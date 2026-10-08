"""Background scheduler: delivers due reminders. Runs in-process; the keep-warm ping keeps the host awake."""
import logging
import threading
import time
from datetime import timedelta

import cr_db as db
from cr_safety import redact

log = logging.getLogger("crayon.sched")
_started = False


def tick(out=None, only_user=None):
    """Deliver due reminders. Returns list of delivered ids. `out` is a sender with .send(chat_id, text)."""
    if out is None:
        import cr_telegram as tg
        out = tg.Out()
    db.q("UPDATE reminders SET status='pending' WHERE status='sending' AND claimed_at < now() - interval '3 minutes'", (), "none")
    cond, params = ("AND user_id=%s", (only_user,)) if only_user is not None else ("", ())
    rows = db.q(f"""UPDATE reminders SET status='sending', claimed_at=now() WHERE id IN (
                      SELECT id FROM reminders WHERE status='pending' AND due_at <= now() {cond}
                      ORDER BY due_at LIMIT 10 FOR UPDATE SKIP LOCKED) RETURNING *""", params)
    delivered = []
    for r in rows:
        late = (db.q("SELECT now() AS n", (), "one")["n"] - r["due_at"]).total_seconds()
        late_note = f"\n(sent {int(late // 60)} min late, the free host was asleep)" if late > 300 else ""
        try:
            if r.get("kind") == "job":
                import cr_agent
                reply, _meta = cr_agent.respond(r["user_id"], r["chat_id"],
                    "[Scheduled job you set for me earlier - do it now and reply with the result only, don't create new reminders or jobs] " + r["text"], "")
                text = "Scheduled: " + reply + late_note
            else:
                text = "Reminder: " + r["text"] + late_note
            out.send(r["chat_id"], text)
        except Exception as e:
            attempts = (r["attempts"] or 0) + 1
            log.warning("reminder %s send failed (%s)", r["id"], redact(str(e))[:120])
            db.q("UPDATE reminders SET status=%s, attempts=%s WHERE id=%s", ("failed" if attempts >= 5 else "pending", attempts, r["id"]), "none")
            continue
        if r["recurrence"] in ("daily", "weekly"):
            step = timedelta(days=1 if r["recurrence"] == "daily" else 7)
            db.q("UPDATE reminders SET status='pending', due_at=due_at + %s, sent_at=now(), attempts=0 WHERE id=%s", (step, r["id"]), "none")
        else:
            db.q("UPDATE reminders SET status='sent', sent_at=now() WHERE id=%s", (r["id"],), "none")
        delivered.append(r["id"])
    return delivered


def _loop():
    while True:
        try:
            tick()
        except Exception as e:
            log.warning("tick failed: %s", redact(f"{type(e).__name__}: {e}")[:200])
        time.sleep(20)


def start():
    global _started
    if _started:
        return
    _started = True
    threading.Thread(target=_loop, daemon=True, name="scheduler").start()
    log.info("scheduler started")
