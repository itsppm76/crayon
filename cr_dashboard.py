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
    lines+=['','Add: /tasks add Title | step1 | step2','Export: /tasks export','Use /tasks show ID or /tasks done ID STEP | result.','Use /work for bounded background research/maths.']
    return '\n'.join(lines)

def handle(uid,chat,text,out):
    if text.strip().lower() in ('my tasks','task dashboard','what should i work on next?','what should i work on next','list my pending tasks'):text='/tasks'
    if not (text=='/tasks' or text.startswith('/tasks ')):return False
    try:
        parts=text.split(None,3)
        if len(parts)==1:out.send(chat,render(uid))
        elif parts[1]=='add':
            T.mem.touch_user(uid)
            fields=[x.strip() for x in text[len('/tasks add '):].split(' | ')]
            if not 2<=len(fields)<=9 or any(not x for x in fields):raise ValueError('Use /tasks add Title | step1 | step2 (up to8 steps).')
            r=T.create_task({'uid':uid,'chat_id':chat},fields[0],fields[1:])
            if not r['verified']:raise ValueError(r.get('error','Task not confirmed'))
            out.send(chat,'Task saved and checked.\n\n'+render(uid))
        elif parts[1]=='export':
            tasks=T.list_tasks({'uid':uid})['tasks']
            if not tasks:raise ValueError('No active tasks to export.')
            import cr_artifacts
            records=[]
            for t in tasks:
                for step in t['steps']:records.append([str(t['id']),t['title'],str(step['n']),step['title'],step['status'],step['result']])
            if len(records)>100:raise ValueError('Too many task rows for this bounded export.')
            out.artifact(chat,{'filename':'crayon-tasks.csv','mime':'text/csv','data':cr_artifacts.csv_bytes(['task_id','task','step','title','status','reported_result'],records)})
            chart=cr_artifacts.chart_bytes('Your recorded task progress',[t['title'][:22] for t in tasks[:12]],[100*t['done']/max(1,t['total']) for t in tasks[:12]],'% complete')
            out.artifact(chat,{'filename':'crayon-task-progress.png','mime':'image/png','data':chart})
            out.send(chat,'Task CSV and recorded-progress chart prepared. Step completion reflects recorded results, not independent proof.')
        elif parts[1]=='show':
            r=T.list_tasks({'uid':uid},int(parts[2]))
            if not r['verified']:raise ValueError('No such task in your account')
            t=r['task'];lines=[f"TASK #{t['id']}: {t['title']}",t['goal']]
            for s in t['steps']:lines+=['',f"{s['n']}. {s['title']} [{s['status']}]",s['result']]
            out.send(chat,'\n'.join(lines))
        elif parts[1] in ('done','doing','blocked','todo'):
            if len(parts)<4 or ' | ' not in parts[3]:raise ValueError('Use /tasks done/doing/blocked/todo ID STEP | your status note. Only mark done when finished.')
            step,note=parts[3].split(' | ',1)
            if not note.strip():raise ValueError('Add a completion note.')
            r=T.update_step({'uid':uid},int(parts[2]),int(step),parts[1],note[:600])
            if not r['verified']:raise ValueError(r.get('error','Update unverified'))
            out.send(chat,'Your status note was saved. This is your reported result, not independently checked.\n\n'+render(uid))
        else:raise ValueError('Use /tasks, add Title | steps, export, show ID, or done ID STEP | result.')
    except Exception as e:out.send(chat,'Task request not completed: '+str(e)[:200])
    return True
