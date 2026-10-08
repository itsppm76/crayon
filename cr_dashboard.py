"""Deterministic private task dashboard and explicit step controls."""
import re
import cr_tools as T
import cr_db as db

def render(uid):
    tasks=T.list_tasks({'uid':uid})['tasks'];reminders=T.list_reminders({'uid':uid})['reminders']
    lines=['YOUR TASKS']
    if not tasks:lines+=['No active tracked tasks.']
    for t in tasks[:8]:
        blocked=[s for s in t['steps'] if s['status']=='blocked'];nxt=next((s for s in t['steps'] if s['status'] in ('todo','doing')),None)
        lines+=['',f"#{t['id']} {t['title']}",f"Progress: {t['done']}/{t['total']}"]
        if blocked:lines+=['Blocked: '+blocked[0]['title']]
        if nxt:lines+=['Next '+str(nxt['n'])+': '+nxt['title']]
    if reminders:
        lines+=['','UPCOMING REMINDERS']
        for r in reminders[:5]:lines+=[r['due_local']+' - '+r['text']]
    import cr_work
    cr_work.init();rows=db.q("SELECT * FROM work_jobs WHERE user_id=%s AND status IN ('queued','running','pausing','paused','blocked') ORDER BY created_at LIMIT 5",(uid,))
    if rows:
        lines+=['','INTERNAL WORK QUEUE']
        lines+=[f"#{r['id']} {r['status']}: {r['title']} ({len(r['results'])}/{len(r['steps'])})" for r in rows]
    lines+=['','Use /tasks show ID or /tasks done ID STEP | result.','Use /work for bounded background research/maths.']
    return '\n'.join(lines)

def handle(uid,chat,text,out):
    if text.strip().lower() in ('my tasks','task dashboard','what should i work on next?','what should i work on next','list my pending tasks'):text='/tasks'
    if not (text=='/tasks' or text.startswith('/tasks ')):return False
    try:
        parts=text.split(None,3)
        if len(parts)==1:out.send(chat,render(uid))
        elif parts[1]=='show':
            r=T.list_tasks({'uid':uid},int(parts[2]))
            if not r['verified']:raise ValueError('No such task in your account')
            t=r['task'];lines=[f"TASK #{t['id']}: {t['title']}",t['goal']]
            for s in t['steps']:lines+=['',f"{s['n']}. {s['title']} [{s['status']}]",s['result']]
            out.send(chat,'\n'.join(lines))
        elif parts[1]=='done':
            if len(parts)<4 or ' | ' not in parts[3]:raise ValueError('Use /tasks done ID STEP | your completion note. Only mark work you actually finished.')
            step,note=parts[3].split(' | ',1)
            if not note.strip():raise ValueError('Add a completion note.')
            r=T.update_step({'uid':uid},int(parts[2]),int(step),'done',note[:600])
            if not r['verified']:raise ValueError(r.get('error','Update unverified'))
            out.send(chat,'Your completion note was saved. This is your reported result, not independently checked.\n\n'+render(uid))
        else:raise ValueError('Use /tasks, show ID, or done ID STEP | result.')
    except Exception as e:out.send(chat,'Task request not completed: '+str(e)[:200])
    return True
