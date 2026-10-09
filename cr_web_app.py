"""Authenticated private web transport. No Telegram sends in request handling.
Foundation stage deliberately blocks external effects and room actions.
"""
import base64
import json
import secrets
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import cr_config as C
import cr_db as db
import cr_web_auth as auth
from cr_safety import clean_text, looks_like_secret

POOL = ThreadPoolExecutor(max_workers=3)
SLOTS = threading.BoundedSemaphore(8)
SCHEMA = '''CREATE TABLE IF NOT EXISTS web_requests(
 id TEXT NOT NULL,user_id BIGINT NOT NULL,state TEXT NOT NULL DEFAULT 'queued',
 encrypted TEXT NOT NULL,created_at TIMESTAMPTZ DEFAULT now(),updated_at TIMESTAMPTZ DEFAULT now(),
 PRIMARY KEY(user_id,id));'''


def init():
    auth.init()
    __import__('cr_web_actions').init()
    db.q(SCHEMA, fetch='none')


def encode(value):
    return auth._cipher().encrypt(json.dumps(value, default=str).encode()).decode()


def decode(value):
    return json.loads(auth._cipher().decrypt(value.encode()))


class WebOut:
    def __init__(self):
        self.items = []
        self.bytes = 0
    def send(self, chat_id, text, markup=None):
        if len(self.items) >= 30: raise ValueError('Too many response items.')
        self.items.append({'kind':'text','text':clean_text(text)[:16000]})
    def artifact(self, chat_id, item):
        self.bytes += len(item['data'])
        if self.bytes > 4000000 or len(self.items) >= 30 or len(item['data']) > 2000000:
            raise ValueError('Artifact exceeds 2 MB.')
        import os
        self.items.append({'kind':'artifact','name':os.path.basename(item['filename'])[:100],
            'mime':item['mime'],'data':base64.b64encode(item['data']).decode()})
        return len(self.items)
    def typing(self, *args): pass
    def delete(self, *args): return True
    def react(self, *args): return True


def dispatch(uid, name, text):
    import cr_agent as A, cr_memory as M, cr_tools as T, cr_channel
    marker = cr_channel.channel.set('web')
    try:
        with M.user_lock(uid):
            if not db.q('SELECT user_id FROM web_sessions WHERE user_id=%s AND expires_at>now() LIMIT 1',(uid,),'one'):
                raise ValueError('Account was deleted. Start again in Telegram.')
            out = WebOut()
            if looks_like_secret(text):
                return [{'kind':'text','text':'That looks like a secret. It was not sent to the model or saved. Do not paste credentials here.'}]
            M.touch_user(uid, name)
            simple = text.strip().lower()
            if simple in ('my tasks','task dashboard') or text.startswith('/tasks'):
                import cr_dashboard
                cr_dashboard.handle(uid, uid, text, out)
                return out.items
            if simple in ('my reminders','/reminders'):
                rows = T.list_reminders({'uid':uid})['reminders']
                return [{'kind':'text','text':json.dumps(rows, default=str, ensure_ascii=False)}]
            if simple in ('show my memory','/memory'):
                return [{'kind':'text','text':M.render_memory(uid)}]
            if simple in ('help','/help'):
                return [{'kind':'text','text':'Web foundation: chat, shared memory, notes, tasks, research, calculations, CSV/charts and reminders. Reminders currently arrive in your Telegram DM, not browser push. Uploads use the + button. Google reads and reviewed sends use Menu > Connections / actions. Computer and group rooms are not enabled.'}]
            # Do not fall into the model for features whose channel review is not implemented yet.
            import re
            if re.search(r'(?i)\b(gmail|inbox|email|e-mail|calendar|google|workspace|github|sheet|doc|computer|browser|browse|booking|book|delete|wipe|forget|digest|proactive|watch)\b', text) or text.startswith(('/email','/google','/connect','/calendar','/work','/delete','/forget')):
                return [{'kind':'text','text':'For Google reads, email/calendar/Sheet previews use Menu > Connections / actions. Computer, rooms and deletion are not enabled in web chat. No external action was made.'}]
            if simple in ('yes','confirm','go ahead','do it','send it'):
                return [{'kind':'text','text':'Web confirmations are not enabled yet. Nothing was sent or deleted.'}]
            # Never consume a pending action created in another channel.
            reply, meta = A.respond(uid, uid, text, name, channel_name='web')
            out.send(uid, reply)
            for item in meta.get('artifacts', []):
                out.artifact(uid, item)
            return out.items
    finally:
        cr_channel.channel.reset(marker)


def submit(user, body):
    text, ident = body.get('message'), body.get('request_id')
    if set(body) != {'message','request_id'} or not isinstance(text,str) or not 1 <= len(text.strip()) <= 8000 or not isinstance(ident,str) or not auth.PATTERN.fullmatch(ident):
        raise ValueError('Invalid message request.')
    uid = user['user_id']
    if looks_like_secret(text):
        raise ValueError('Do not send passwords, keys or credentials here.')
    old = db.q('SELECT state FROM web_requests WHERE user_id=%s AND id=%s', (uid,ident), 'one')
    if old:
        return {'request_id':ident,'state':old['state']}
    count = db.q("SELECT (SELECT count(*) FROM web_requests WHERE user_id=%s AND created_at>now()-interval '24 hours')+(SELECT count(*) FROM messages WHERE user_id=%s AND role='user' AND ts>now()-interval '24 hours') AS n", (uid,uid), 'one')['n']
    if count >= C.DAILY_MESSAGE_CAP:
        raise ValueError('Daily free-tier message limit reached.')
    if not SLOTS.acquire(blocking=False):
        raise ValueError('Crayon is busy. Wait before sending another request.')
    try:
        row = db.q('INSERT INTO web_requests(id,user_id,encrypted) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING RETURNING id',
            (ident,uid,encode({'input':text,'name':user['name']})), 'one')
        if row:
            POOL.submit(_run,uid,ident)
        else:
            SLOTS.release()
    except Exception:
        SLOTS.release()
        raise
    return {'request_id':ident,'state':'queued'}


def _run(uid, ident):
    try:
        row = db.q("UPDATE web_requests SET state='running',updated_at=now() WHERE user_id=%s AND id=%s AND state='queued' RETURNING encrypted",(uid,ident),'one')
        if not row: return
        data = decode(row['encrypted'])
        try:
            items = dispatch(uid,data['name'],data['input'])
            status = 'done'
        except Exception:
            items = [{'kind':'text','text':'Request stopped. Its outcome is unconfirmed. Check your records before trying again.'}]
            status = 'blocked'
        db.q('UPDATE web_requests SET state=%s,encrypted=%s,updated_at=now() WHERE user_id=%s AND id=%s',
             (status,encode({'items':items}),uid,ident),'none')
    finally:
        SLOTS.release()


def result(uid, ident):
    if not isinstance(ident,str) or not auth.PATTERN.fullmatch(ident): raise ValueError('Invalid request ID.')
    row = db.q('SELECT state,encrypted,updated_at FROM web_requests WHERE user_id=%s AND id=%s', (uid,ident),'one')
    if not row: raise ValueError('Request not found in your account.')
    state = row['state']
    if state in ('queued','running') and (datetime.now(row['updated_at'].tzinfo)-row['updated_at']).total_seconds()>300:
        # No automatic rerun of interrupted effects.
        state = 'blocked'
    return {'request_id':ident,'state':state,'items':decode(row['encrypted']).get('items',[]) if state in ('done','blocked') else []}


def activity(uid):
    # Requests may include private results, so output is encrypted at rest and owner-scoped.
    rows = db.q('SELECT id,state,encrypted,created_at FROM web_requests WHERE user_id=%s ORDER BY created_at DESC LIMIT 30', (uid,))
    return [{'id':r['id'],'state':r['state'],'created_at':str(r['created_at']),
        'items':decode(r['encrypted']).get('items',[]) if r['state'] in ('done','blocked') else []} for r in reversed(rows)]


def history(uid, before=None):
    if before is not None and (not isinstance(before,str) or not before.isdigit() or not 0<int(before)<10**18):
        raise ValueError('Invalid history cursor.')
    rows=db.q('SELECT id,role,content,ts FROM messages WHERE user_id=%s'+(' AND id<%s' if before else '')+' ORDER BY id DESC LIMIT 51',
              (uid,int(before)) if before else (uid,))
    page=rows[:50]
    return {'messages':list(reversed([{'id':r['id'],'role':r['role'],'text':r['content'],'time':str(r['ts']),
        'media_missing':r['content'].startswith('[User sent media:')} for r in page])),
        'has_more':len(rows)>50,'before':str(page[-1]['id']) if page else None}


def upload(user, body):
    import os, cr_media
    if set(body)!={'data','mime','name','caption','request_id'}:
        raise ValueError('Invalid upload fields.')
    if not isinstance(body['name'],str) or not 1<=len(body['name'])<=200 or not isinstance(body['mime'],str) or len(body['mime'])>100:
        raise ValueError('Invalid file metadata.')
    if not isinstance(body['caption'],str) or len(body['caption'])>8000 or looks_like_secret(body['caption']):
        raise ValueError('Invalid caption or secret detected.')
    if not isinstance(body['data'],str) or len(body['data'])>26666672:
        raise ValueError('Upload limit is 20 MB.')
    try: data=base64.b64decode(body['data'],validate=True)
    except Exception: raise ValueError('Invalid upload encoding.') from None
    if not data or len(data)>cr_media.MAX_BYTES:raise ValueError('Upload limit is 20 MB.')
    ident=body['request_id'];uid=user['user_id']
    if not isinstance(ident,str) or not auth.PATTERN.fullmatch(ident):raise ValueError('Invalid request ID.')
    old=db.q('SELECT state FROM web_requests WHERE user_id=%s AND id=%s',(uid,ident),'one')
    if old:return {'request_id':ident,'state':old['state']}
    count=db.q("SELECT (SELECT count(*) FROM web_requests WHERE user_id=%s AND created_at>now()-interval '24 hours')+(SELECT count(*) FROM messages WHERE user_id=%s AND role='user' AND ts>now()-interval '24 hours') AS n",(uid,uid),'one')['n']
    if count>=C.DAILY_MESSAGE_CAP:raise ValueError('Daily free-tier message limit reached.')
    if not SLOTS.acquire(blocking=False):raise ValueError('Crayon is busy. Wait before uploading.')
    name=os.path.basename(body['name']);mime=cr_media.normalize_mime(body['mime'],name)
    try:
        row=db.q('INSERT INTO web_requests(id,user_id,encrypted) VALUES(%s,%s,%s) ON CONFLICT DO NOTHING RETURNING id',
            (ident,uid,encode({'name':name,'mime':mime,'bytes':len(data),'caption':body['caption'],'raw_retained':False})),'one')
        if row:POOL.submit(_upload_run,uid,ident,user['name'],data,mime,name,body['caption'])
        else:SLOTS.release()
    except Exception:SLOTS.release();raise
    return {'request_id':ident,'state':'queued'}


def _upload_run(uid,ident,username,data,mime,name,caption):
    try:
        row=db.q("UPDATE web_requests SET state='running',updated_at=now() WHERE user_id=%s AND id=%s AND state='queued' RETURNING id",(uid,ident),'one')
        if not row:return
        import cr_media,cr_memory as M
        try:
            with M.user_lock(uid):
                if not db.q('SELECT user_id FROM web_sessions WHERE user_id=%s AND expires_at>now() LIMIT 1',(uid,),'one'):raise ValueError('Account was deleted.')
                M.touch_user(uid,username)
                response=cr_media.analyze(data,mime,caption,name)
                M.add_message(uid,'user','[User sent media: '+mime+'] '+name+' '+caption)
                M.add_message(uid,'assistant','[Media analysis summary; raw file not retained] '+clean_text(response)[:3000])
            items=[{'kind':'text','text':clean_text(response)}];state='done'
        except Exception as e:
            items=[{'kind':'text','text':'Upload stopped: '+(str(e)[:200] if isinstance(e,ValueError) else 'Media processing failed. No analysis confirmed.')}];state='blocked'
        db.q('UPDATE web_requests SET state=%s,encrypted=%s,updated_at=now() WHERE user_id=%s AND id=%s',
             (state,encode({'items':items,'file_receipt':{'name':name,'mime':mime,'bytes':len(data),'raw_retained':False}}),uid,ident),'none')
    finally:SLOTS.release()
