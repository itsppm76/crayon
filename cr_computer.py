"""Owner-only outbound computer bridge. No shell, GitHub tokens or public ports."""
import json,os,time,uuid
import cr_db as db
OWNER=1898030949
TESTERS={7555366869}
def permitted(uid):return uid==OWNER or uid in TESTERS
SCHEMA="""CREATE TABLE IF NOT EXISTS computer_jobs(id TEXT PRIMARY KEY,operation TEXT NOT NULL,args JSONB NOT NULL,status TEXT NOT NULL DEFAULT 'pending',result JSONB,created_at TIMESTAMPTZ DEFAULT now());"""
def init():
    db.q(SCHEMA,(),"none")
    db.q("CREATE TABLE IF NOT EXISTS computer_usage(day DATE,user_id BIGINT,used INT DEFAULT 0,PRIMARY KEY(day,user_id))",(),"none")
def reserve(uid):
    # A single transaction lock serializes global/user checks across threads/processes.
    conn=db._connect()
    try:
        with conn.transaction():
            conn.execute("SELECT pg_advisory_xact_lock(39272411)")
            row=conn.execute("SELECT COALESCE(sum(used),0) AS total FROM computer_usage WHERE day=CURRENT_DATE").fetchone()
            own=conn.execute("SELECT used FROM computer_usage WHERE day=CURRENT_DATE AND user_id=%s",(uid,)).fetchone()
            cap=20 if uid==OWNER else 5
            if row['total']>=30 or (own and own['used']>=cap):return False
            conn.execute("INSERT INTO computer_usage(day,user_id,used) VALUES(CURRENT_DATE,%s,1) ON CONFLICT(day,user_id) DO UPDATE SET used=computer_usage.used+1",(uid,))
            conn.execute("DELETE FROM computer_usage WHERE day<CURRENT_DATE-7")
            return True
    finally:conn.close()
def validate(operation,args):
    if operation not in ('status','calculate','write_text','read_text','list_files','browse'):raise ValueError('Unsupported computer operation')
    if not isinstance(args,dict):raise ValueError('Invalid arguments')
    if operation=='browse':
        from computer_browser import validate_plan
        validate_plan(args)
    if len(json.dumps(args))>20000:raise ValueError('Computer input too large')
    if operation in ('read_text','write_text'):
        import re
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}',args.get('filename','')):raise ValueError('Use a plain filename, no folders')
    if operation=='write_text' and (not isinstance(args.get('text'),str) or len(args['text'])>12000):raise ValueError('Text limit is12000 characters')
    if operation=='calculate' and (not isinstance(args.get('expression'),str) or len(args['expression'])>200):raise ValueError('Use a short arithmetic expression')
    return args

def status(uid):
    if not permitted(uid):return {'ok':False,'error':'Computer beta is available only to approved testers.'}
    row=db.kv_get('computer_heartbeat') or {}
    fresh=time.time()-row.get('at',0)<60
    return {'ok':fresh,'verified':fresh,'state':'awake' if fresh else 'offline or asleep','computer':row.get('info',{}) if uid==OWNER else {},'note':'No automatic restart. Free allowance and sleep apply.'}

def execute(uid,operation,args):
    if not permitted(uid):return {'ok':False,'error':'Approved tester-only computer beta'}
    if uid!=OWNER and operation not in ('status','calculate','browse'):return {'ok':False,'error':'Text files are private to the owner. Testers can use public browser and arithmetic only.'}
    validate(operation,args)
    if not status(uid)['ok']:return {'ok':False,'error':'Computer is asleep or not connected. Owner must start it in GitHub Codespaces.'}
    if not reserve(uid):return {'ok':False,'error':'Daily computer beta cap reached.5 jobs per tester,20 owner,30 total. No automatic wake.'}
    job=uuid.uuid4().hex
    db.q('INSERT INTO computer_jobs(id,operation,args) VALUES(%s,%s,%s::jsonb)',(job,operation,json.dumps(args)),'none')
    for _ in range(85 if operation=='browse' else 25):
        row=db.q('SELECT status,result FROM computer_jobs WHERE id=%s',(job,),'one')
        if row and row['status']=='done':return row['result']
        time.sleep(1)
    db.q("UPDATE computer_jobs SET status='expired' WHERE id=%s AND status='pending'",(job,),'none')
    return {'ok':False,'verified':False,'error':'No completion confirmed. Do not retry writes automatically.'}

def next_job(info):
    # Browser payloads and task text are transient, not durable memory.
    db.q("DELETE FROM computer_jobs WHERE created_at<now()-interval '30 minutes'",(),'none')
    db.kv_set('computer_heartbeat',{'at':time.time(),'info':info})
    return db.q("UPDATE computer_jobs SET status='running' WHERE id=(SELECT id FROM computer_jobs WHERE status='pending' AND created_at>now()-interval '40 seconds' ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING id,operation,args",(),'one')

def complete(job,result):
    if not isinstance(result,dict) or len(json.dumps(result))>1500000:raise ValueError('Invalid result')
    db.q("UPDATE computer_jobs SET status='done',result=%s::jsonb WHERE id=%s AND status='running'",(json.dumps(result),job),'none')
