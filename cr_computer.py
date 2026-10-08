"""Owner-only outbound computer bridge. No shell, GitHub tokens or public ports."""
import json,os,time,uuid
import cr_db as db
OWNER=1898030949
SCHEMA="""CREATE TABLE IF NOT EXISTS computer_jobs(id TEXT PRIMARY KEY,operation TEXT NOT NULL,args JSONB NOT NULL,status TEXT NOT NULL DEFAULT 'pending',result JSONB,created_at TIMESTAMPTZ DEFAULT now());"""
def init():db.q(SCHEMA,(),"none")
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
    if uid!=OWNER:return {'ok':False,'error':'This computer belongs to the bot owner, not other users.'}
    row=db.kv_get('computer_heartbeat') or {}
    fresh=time.time()-row.get('at',0)<60
    return {'ok':fresh,'verified':fresh,'state':'awake' if fresh else 'offline or asleep','computer':row.get('info',{}),'note':'No automatic restart. Free allowance and sleep apply.'}

def execute(uid,operation,args):
    if uid!=OWNER:return {'ok':False,'error':'Owner-only computer'}
    validate(operation,args)
    if not status(uid)['ok']:return {'ok':False,'error':'Computer is asleep or not connected. Owner must start it in GitHub Codespaces.'}
    job=uuid.uuid4().hex
    db.q('INSERT INTO computer_jobs(id,operation,args) VALUES(%s,%s,%s::jsonb)',(job,operation,json.dumps(args)),'none')
    for _ in range(85 if operation=='browse' else 25):
        row=db.q('SELECT status,result FROM computer_jobs WHERE id=%s',(job,),'one')
        if row and row['status']=='done':return row['result']
        time.sleep(1)
    db.q("UPDATE computer_jobs SET status='expired' WHERE id=%s AND status='pending'",(job,),'none')
    return {'ok':False,'verified':False,'error':'No completion confirmed. Do not retry writes automatically.'}

def next_job(info):
    db.kv_set('computer_heartbeat',{'at':time.time(),'info':info})
    return db.q("UPDATE computer_jobs SET status='running' WHERE id=(SELECT id FROM computer_jobs WHERE status='pending' AND created_at>now()-interval '40 seconds' ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1) RETURNING id,operation,args",(),'one')

def complete(job,result):
    if not isinstance(result,dict) or len(json.dumps(result))>1500000:raise ValueError('Invalid result')
    db.q("UPDATE computer_jobs SET status='done',result=%s::jsonb WHERE id=%s AND status='running'",(json.dumps(result),job),'none')
