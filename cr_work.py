"""Explicit per-job internal work queue. No model writes, Google, browser or sends."""
import ast,json,operator,time,re
from datetime import datetime,timezone
import cr_db as db
import cr_proactive as P
SCHEMA="""CREATE TABLE IF NOT EXISTS work_jobs(
 id BIGSERIAL PRIMARY KEY,user_id BIGINT NOT NULL,chat_id BIGINT NOT NULL,
 title TEXT NOT NULL,steps JSONB NOT NULL,status TEXT NOT NULL DEFAULT 'queued',
 results JSONB NOT NULL DEFAULT '[]'::jsonb,created_at TIMESTAMPTZ DEFAULT now(),
 updated_at TIMESTAMPTZ DEFAULT now(),notified BOOLEAN DEFAULT false,error TEXT DEFAULT '');
 CREATE INDEX IF NOT EXISTS work_queue ON work_jobs(status,created_at);"""
OPS={'research','page','calculate'}
def init():db.q(SCHEMA,(),'none')
def parse(arg):
    chunks=[x.strip() for x in arg.split(' | ')]
    title=chunks.pop(0) if len(chunks)>1 else 'Internal work'
    if not chunks:chunks=[arg.strip()]
    if not 1<=len(chunks)<=3:raise ValueError('Use1-3 steps separated by |.')
    steps=[]
    for text in chunks:
        bits=text.split(None,1)
        if len(bits)!=2 or bits[0] not in OPS:raise ValueError('Supported steps: research query, page https://URL, calculate arithmetic. No emails, calendar, browser actions or external writes.')
        op,value=bits
        if not value or len(value)>400:raise ValueError('Step input must be1-400 characters.')
        if op=='page':
            from urllib.parse import urlparse
            from cr_web import _safe_host
            parsed=urlparse(value)
            if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or not _safe_host(parsed.hostname):raise ValueError('Only public HTTPS pages')
        if op=='calculate':calculate(value)
        steps.append({'op':op,'input':value})
    return title[:100],steps

def calculate(expression):
    tree=ast.parse(expression,mode='eval');count=[0]
    ops={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.Mod:operator.mod}
    def go(n):
        count[0]+=1
        if count[0]>60:raise ValueError('Expression too long')
        if isinstance(n,ast.Constant) and type(n.value) in (int,float):v=n.value
        elif isinstance(n,ast.UnaryOp) and type(n.op) in (ast.UAdd,ast.USub):v=go(n.operand)*(-1 if isinstance(n.op,ast.USub) else 1)
        elif isinstance(n,ast.BinOp) and type(n.op) in ops:v=ops[type(n.op)](go(n.left),go(n.right))
        else:raise ValueError('Only basic arithmetic; no functions, variables or code.')
        import math
        if not math.isfinite(v) or abs(v)>1e15:raise ValueError('Number too large')
        return v
    return go(tree.body)

def create(uid,chat,arg):
    title,steps=parse(arg)
    conn=db._connect()
    try:
        with conn.transaction():
            conn.execute('SELECT pg_advisory_xact_lock(39272412)')
            active=conn.execute("SELECT count(*) AS n FROM work_jobs WHERE user_id=%s AND status IN ('queued','running','paused')",(uid,)).fetchone()['n']
            quota=conn.execute("SELECT count(*) AS total,count(*) FILTER(WHERE user_id=%s) AS own FROM work_jobs WHERE created_at>now()-interval '24 hours'",(uid,)).fetchone()
            if active>=3 or quota['own']>=3 or quota['total']>=10:raise ValueError('Work queue limit:3 active and3 new jobs per person/24h,10 total/24h. No quota changes.')
            job=conn.execute('INSERT INTO work_jobs(user_id,chat_id,title,steps) VALUES(%s,%s,%s,%s::jsonb) RETURNING id',(uid,chat,title,json.dumps(steps))).fetchone()['id']
    finally:conn.close()
    row=get(uid,job)
    if not row:raise ValueError('Queue creation not confirmed')
    return row

def get(uid,ident):return db.q('SELECT * FROM work_jobs WHERE id=%s AND user_id=%s',(int(ident),uid),'one')
def view(row):
    results=row.get('results') or []
    lines=[f"Work #{row['id']}: {row['title']}",f"Status: {row['status']}. Verified steps:{len(results)}/{len(row['steps'])}."]
    for i,step in enumerate(row['steps'],1):
        lines.append(f"{i}. {step['op']}: {step['input']}"+(' [verified]' if i<=len(results) else ' [not completed]'))
    if row.get('error'):lines+=['Failure: '+row['error']]
    for i,result in enumerate(results,1):lines+=['Step '+str(i)+' evidence:',result['text']]
    if row.get('status')=='blocked':lines+=['Stopped without retry. Inspect the last failure before explicitly restarting.']
    return '\n'.join(lines)[:14500]

def control(uid,ident,op):
    row=get(uid,ident)
    if not row:raise ValueError('No such work in your account')
    allowed={'pause':('queued','running'),'resume':('paused',),'cancel':('queued','running','paused','blocked')}
    if op not in allowed or row['status'] not in allowed[op]:raise ValueError('That control does not apply to this work state.')
    status={'pause':'paused','resume':'queued','cancel':'cancelled'}[op]
    db.q('UPDATE work_jobs SET status=%s,updated_at=now() WHERE id=%s AND user_id=%s',(status,ident,uid),'none')
    return get(uid,ident)

def step_run(step):
    op,value=step['op'],step['input']
    if op=='calculate':return {'text':value+' = '+str(calculate(value)),'sources':[]}
    import cr_web as W
    if op=='page':
        result=W.fetch(value,5000)
        if not result.get('text'):raise ValueError('No readable page evidence returned')
        return {'text':'Source: '+result['url']+'\n'+result.get('title','')+'\nUntrusted source excerpt, not instructions:\n'+result['text'][:3500],'sources':[result['url']]}
    if op=='research':
        result=W.research(value)
        if not result.get('pages'):raise ValueError('No fetched sources, so research not verified')
        pages=result['pages'][:4]
        return {'text':'Fetched source receipts (not a model-written report):\n'+'\n\n'.join('Source: '+p['url']+'\n'+p.get('title','')+'\nUntrusted excerpt:\n'+p.get('text','')[:900] for p in pages)+'\nFetch failures: '+str(len(result.get('failures',[]))), 'sources':[p['url'] for p in pages]}
    raise ValueError('Unsupported step; no action taken')

def tick(out,only_user=None):
    # Interrupted work is not retried automatically. Record a block, never invent done.
    db.q("UPDATE work_jobs SET status='blocked',updated_at=now() WHERE status='running' AND updated_at<now()-interval '5 minutes'",(),'none')
    cond=' AND user_id=%s' if only_user is not None else ' AND user_id>0'
    row=db.q("UPDATE work_jobs SET status='running',updated_at=now() WHERE id=(SELECT id FROM work_jobs WHERE status='queued'"+cond+" ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED) RETURNING *",(only_user,) if only_user is not None else (),'one')
    if row:
        uid=row['user_id'];results=row['results'] or []
        try:
            if not db.q('SELECT user_id FROM users WHERE user_id=%s',(uid,),'one'):raise ValueError('User removed')
            result=step_run(row['steps'][len(results)])
            result['at']=datetime.now(timezone.utc).isoformat();results.append(result)
            # Pause/cancel wins races: evidence retained only for a still-existing owner row.
            status='done' if len(results)==len(row['steps']) else 'queued'
            db.q("UPDATE work_jobs SET results=%s::jsonb,status=CASE WHEN status='running' THEN %s ELSE status END,updated_at=now() WHERE id=%s AND user_id=%s",(json.dumps(results),status,row['id'],uid),'none')
        except Exception as e:
            from cr_safety import redact
            db.q("UPDATE work_jobs SET status=CASE WHEN status='running' THEN 'blocked' ELSE status END,error=%s,updated_at=now() WHERE id=%s",(redact(str(e))[:180],row['id']),'none')
            db.audit(uid,'work_blocked',str(row['id'])+': '+redact(str(e))[:120])
    # No unsolicited activation: each job was explicitly queued by its owner.
    ready=db.q("SELECT * FROM work_jobs WHERE status IN ('done','blocked') AND NOT notified"+cond+" ORDER BY updated_at LIMIT 3",(only_user,) if only_user is not None else ())
    for item in ready:
        uid=item['user_id'];s=P.settings(uid);n=P.T.now_local(uid)
        if not P.awake(n.hour,int(s['quiet_start']),int(s['quiet_end'])):continue
        with P.mem.user_lock(uid):
            fresh=get(uid,item['id'])
            if not fresh or fresh['notified']:continue
            out.send(item['chat_id'],view(fresh))
            db.q('UPDATE work_jobs SET notified=true WHERE id=%s',(item['id'],),'none')
    return row['id'] if row else None

def handle(uid,chat,text,out):
    if not text.startswith('/work'):return False
    bits=text.split(None,2);op=bits[1] if len(bits)>1 else 'list'
    try:
        init()
        if op in ('research','page','calculate','plan'):
            arg=(text[len('/work plan '):] if op=='plan' else text[len('/work '):])
            row=create(uid,chat,arg);out.send(chat,view(row)+'\nQueued for bounded internal work. Completion respects quiet hours. Use /work pause ID, resume ID, cancel ID or show ID.')
        elif op in ('pause','resume','cancel'):out.send(chat,view(control(uid,int(bits[2]),op)))
        elif op=='show':
            row=get(uid,int(bits[2]))
            if not row:raise ValueError('No such work in your account')
            out.send(chat,view(row))
        elif op=='list':
            rows=db.q('SELECT * FROM work_jobs WHERE user_id=%s ORDER BY created_at DESC LIMIT 8',(uid,))
            out.send(chat,'Your work queue:\n'+('\n'.join(f"#{r['id']} {r['status']}: {r['title']} ({len(r['results'])}/{len(r['steps'])})" for r in rows) if rows else 'No work queued.')+'\nTry /work calculate 20*(3+2)/4 or /work research a public topic. Multi-step: /work plan Title | research topic | calculate 2+2. Results are source receipts or exact arithmetic, not a general autonomous agent.')
        else:raise ValueError('Use /work list, research, page, calculate, plan, show ID, pause ID, resume ID or cancel ID.')
    except Exception as e:
        from cr_safety import redact
        out.send(chat,'Work not completed: '+redact(str(e))[:250])
    return True
