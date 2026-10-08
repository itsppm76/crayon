"""Disabled until explicit deployment configuration and least-privilege token exist."""
import os,time,threading
import httpx
import cr_db as db
NAME='bug-free-lamp-pvwpx5j5rjc999p'
API='https://api.github.com/user/codespaces/'+NAME
lock=threading.Lock()
def configured():return os.environ.get('CRAYON_AUTO_WAKE')=='on' and bool(os.environ.get('CRAYON_GITHUB_LIFECYCLE_TOKEN'))
def call(op):
    if not configured():raise ValueError('Auto-wake is not configured')
    if op not in ('start','stop'):raise ValueError('Unsupported lifecycle operation')
    with httpx.Client(timeout=20,follow_redirects=False) as client:
        r=client.post(API+'/'+op,headers={'Authorization':'Bearer '+os.environ['CRAYON_GITHUB_LIFECYCLE_TOKEN'],'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2026-03-10'})
    if r.status_code not in (200,202,204):raise ValueError('Computer lifecycle request blocked (HTTP '+str(r.status_code)+'). No quota or budget changes made.')
    return True
def touch():db.kv_set('computer_last_activity',time.time())
def ensure(ready):
    if ready():touch();return True
    if not configured():return False
    with lock:
        if ready():touch();return True
        # One start request, no retries. API is pinned to one existing machine.
        call('start');touch()
        until=time.monotonic()+120
        while time.monotonic()<until:
            if ready():return True
            time.sleep(3)
    return False
def idle_stop():
    if not configured():return
    with lock:
        at=db.kv_get('computer_last_activity',0)
        if not at or time.time()-at<600:return
        busy=db.q("SELECT id FROM computer_jobs WHERE status IN ('pending','running')  LIMIT 1",(),'one')
        if busy:return
        call('stop');db.kv_set('computer_last_activity',0)
