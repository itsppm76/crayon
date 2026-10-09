"""Opt-in quiet-hour check-ins and digests. No model calls in the scheduler."""
import json
from datetime import timedelta
import cr_db as db
import cr_memory as mem
import cr_tools as T

DEFAULT = {"proactive": False, "digest": "off", "quiet_start": 21, "quiet_end": 9}

def settings(uid):
    u = mem.get_user(uid) or {}
    return {**DEFAULT, **(u.get("settings") or {})}

def set_option(uid, chat_id, key, value):
    mem.touch_user(uid)
    s = settings(uid)
    s[key] = value
    s["chat_id"] = chat_id
    db.q("UPDATE users SET settings=%s::jsonb WHERE user_id=%s", (json.dumps(s), uid), "none")
    return settings(uid).get(key) == value

def awake(hour, start, end):
    if start == end:
        return True
    quiet = start <= hour < end if start < end else hour >= start or hour < end
    return not quiet

def digest_text(uid):
    tasks = T.list_tasks({"uid":uid})["tasks"]
    reminders = T.list_reminders({"uid":uid})["reminders"]
    lines = ["Your digest:"]
    for t in tasks[:5]:
        nxt = next((s["title"] for s in t["steps"] if s["status"] != "done"), "wrap up")
        lines.append(f"Task: {t['title']} ({t['done']}/{t['total']}) - next: {nxt}")
    for r in reminders[:5]:
        lines.append(f"Due {r['due_local']}: {r['text']}")
    rows = db.q("SELECT title FROM tasks WHERE user_id=%s AND status='done' AND updated_at > now()-interval '24 hours' ORDER BY updated_at DESC LIMIT 5", (uid,))
    for r in rows:
        lines.append("Completed task: " + r["title"])
    if len(lines)==1:
        lines.append("No active tasks, pending reminders, or recently completed tasks.")
    return "\n".join(lines)

def tick(out, only_user=None):
    cond = "user_id=%s" if only_user is not None else "user_id>0 AND user_id<1000000000000000"
    rows = db.q("SELECT user_id,settings FROM users WHERE " + cond, (only_user,) if only_user is not None else ())
    sent=[]
    for row in rows:
        uid = row["user_id"]
        s = {**DEFAULT, **(row["settings"] or {})}
        chat_id = s.get("chat_id")
        if not chat_id or not (s.get("proactive") or s.get("digest") != "off"):
            continue
        n = T.now_local(uid)
        if not awake(n.hour, int(s["quiet_start"]), int(s["quiet_end"])):
            continue
        date = n.date().isoformat()
        messages=[]
        mode=s.get("digest", "off")
        period = "morning" if 9 <= n.hour < 12 else "evening" if 18 <= n.hour < 21 else ""
        if period and mode in (period, "both") and s.get("digest_"+period) != date:
            messages.append(("digest_"+period, digest_text(uid), date))
        if s.get("proactive") and s.get("proactive_date") != date:
            stale=db.q("SELECT id,title FROM tasks WHERE user_id=%s AND status='active' AND updated_at < now()-interval '24 hours' ORDER BY updated_at LIMIT 1",(uid,),"one")
            due=db.q("SELECT text FROM reminders WHERE user_id=%s AND status='pending' AND due_at>now() AND due_at<now()+interval '2 hours' ORDER BY due_at LIMIT 1",(uid,),"one")
            if stale:
                messages.append(("proactive_date", "Task check-in: " + stale["title"] + ". Want to continue it or change the plan?", date))
            elif due:
                messages.append(("proactive_date", "Coming up in the next 2 hours: " + due["text"], date))
        for key,text,value in messages[:2]:
            try:
                out.send(chat_id,text)
                # Atomic field update preserves concurrent settings changes.
                db.q("UPDATE users SET settings=jsonb_set(settings,%s,%s::jsonb) WHERE user_id=%s",([key],json.dumps(value),uid),"none")
                sent.append(key)
            except Exception:
                pass
    return sent
