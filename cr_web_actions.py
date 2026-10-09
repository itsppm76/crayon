"""Web-only exact review tickets, session-bound and one-use. Google reads bypass AI/history."""
import json,hashlib,secrets
import cr_db as db
import cr_web_auth as A
import cr_google as G

def init():
    db.q("""CREATE TABLE IF NOT EXISTS web_action_reviews(
      id TEXT PRIMARY KEY,user_id BIGINT NOT NULL,session_hash TEXT NOT NULL,
      encrypted TEXT NOT NULL,content_hash TEXT NOT NULL,status TEXT DEFAULT 'pending',
      expires_at TIMESTAMPTZ NOT NULL)""",fetch='none')

def connections(uid):
    import cr_connections as X
    return {'google':G.status(uid).get('email'),'workspace':(X.status(uid,'workspace') or {}).get('identity'),
      'calendar_owner':bool(G.status(uid)),'external_auto_send':False,'attachments_email':False}

def preview(uid,header,body):
    init()
    if set(body)!={'kind','fields'} or not isinstance(body['fields'],dict):raise ValueError('Invalid action preview.')
    kind,f=body['kind'],body['fields'];payload={}
    if kind=='email':
        if set(f)!={'to','cc','bcc','subject','body'}:raise ValueError('Exact email fields required.')
        d=G.make_draft(uid,f,structured=True,channel='web')
        # Current draft remains encrypted in provider module. This session ticket gates web sends separately.
        payload={'id':d['id'],'hash':d['hash']}
        text=d['text'].split('\n\nReply with edit/change/rewrite instructions')[0]+'\n\nWeb review: Send exactly this once, or Cancel. No email attachments.'
    elif kind=='calendar':
        import cr_calendar_draft as K
        if set(f)!={'title','start','end','timezone','guests','reminder_minutes'}:raise ValueError('Exact calendar fields required.')
        d=K.preview(uid,f['title'],f['start'],f['end'],f['timezone'],guests=f['guests'],reminder_minutes=f['reminder_minutes'],channel='web')
        payload={'id':d['id'],'hash':d['hash']};text=d['text']
    elif kind=='sheet':
        import cr_workspace as S,cr_connections as X
        if set(f)!={'sid','area','values'}:raise ValueError('Exact sheet fields required.')
        d=S.sheet_preview(uid,f['sid'],f['area'],f['values']);payload=d
        text='Sheet update preview only.\nAccount: '+str((X.status(uid,'workspace') or {}).get('identity'))+'\nSpreadsheet: '+f['sid']+'\nRange: '+f['area']+'\nBefore: '+json.dumps(d['payload']['before'])+'\nWrite as RAW values: '+json.dumps(f['values'])+'\nNo formulas. Compare-before-write and readback. Expires in 10 minutes.'
    else:raise ValueError('Action not enabled.')
    data={'kind':kind,'payload':payload,'text':text};digest=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest();ident=secrets.token_urlsafe(24)
    db.q("DELETE FROM web_action_reviews WHERE expires_at<now()",fetch='none')
    db.q("INSERT INTO web_action_reviews(id,user_id,session_hash,encrypted,content_hash,expires_at) VALUES(%s,%s,%s,%s,%s,now()+interval '10 minutes')",
      (ident,uid,A.digest(header[7:]),A._cipher().encrypt(json.dumps(data).encode()).decode(),digest),'none')
    return {'review_id':ident,'hash':digest,'text':text,'kind':kind,'expires_in':600}

def confirm(uid,header,body):
    if set(body)!={'review_id','hash','decision'} or body['decision'] not in ('confirm','cancel') or not isinstance(body['review_id'],str) or not isinstance(body['hash'],str):raise ValueError('Invalid review decision.')
    init()
    row=db.q("UPDATE web_action_reviews SET status='claimed' WHERE id=%s AND user_id=%s AND session_hash=%s AND content_hash=%s AND status='pending' AND expires_at>now() RETURNING encrypted,content_hash",
        (body['review_id'],uid,A.digest(header[7:]),body['hash']),'one')
    if not row:raise ValueError('Review expired, changed, wrong session or already used. No retry.')
    data=json.loads(A._cipher().decrypt(row['encrypted'].encode()))
    if hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()!=row['content_hash']:raise ValueError('Review changed. No action made.')
    kind,p=data['kind'],data['payload']
    try:
        if body['decision']=='cancel':
            if kind=='email':G.cancel_draft(uid,p['id'],channel='web')
            elif kind=='calendar':__import__('cr_calendar_draft').cancel(uid,p['id'],channel='web')
            text='Cancelled. No external action made.'
        elif kind=='email':text=G.send_draft(uid,p['id'],p['hash'],channel='web')
        elif kind=='calendar':text=__import__('cr_calendar_draft').create(uid,p['id'],p['hash'],channel='web')
        elif kind=='sheet':text=json.dumps(__import__('cr_workspace').sheet_apply(uid,p['payload'],p['hash']),ensure_ascii=False)
        else:raise ValueError('Action unavailable.')
        db.q('DELETE FROM web_action_reviews WHERE id=%s AND user_id=%s',(body['review_id'],uid),'none')
        return {'text':text}
    except Exception:
        db.q("UPDATE web_action_reviews SET status='stopped' WHERE id=%s AND user_id=%s",(body['review_id'],uid),'none')
        raise G.GoogleError('Action stopped or uncertain. Check the destination before preparing another request. No automatic retry.') from None

def read(uid,body):
    if set(body)!={'kind','fields'} or not isinstance(body['fields'],dict):raise ValueError('Invalid private read.')
    kind,f=body['kind'],body['fields']
    if kind=='inbox' and set(f)=={'query'} and isinstance(f['query'],str):text=G.inbox(uid,f['query'])
    elif kind=='email_read' and set(f)=={'id'} and isinstance(f['id'],str):text=G.read_message(uid,f['id'])
    elif kind=='calendar' and not f:
        text=G.calendar(uid)
    elif kind=='doc' and set(f)=={'id'}:text=json.dumps(__import__('cr_workspace').doc_read(uid,f['id']),ensure_ascii=False)
    elif kind=='sheet' and set(f)=={'id','range'}:text=json.dumps(__import__('cr_workspace').sheet_read(uid,f['id'],f['range']),ensure_ascii=False)
    else:raise ValueError('Read not enabled or invalid fields.')
    return {'text':text,'private':True,'stored_in_history':False,'sent_to_ai':False}

def connect(uid,body):
    if set(body)!={'provider'}:raise ValueError('Invalid connection request.')
    if body['provider']=='google':url=G.begin(uid)
    elif body['provider']=='calendar_write':
        url=G.begin(uid,calendar_write=True)
    elif body['provider']=='workspace':url=__import__('cr_connections').begin(uid,'workspace')
    else:raise ValueError('Connection not enabled.')
    return {'url':url,'text':'Review provider account and permissions. Return here and check Connections. Do not forward your account-bound link.'}
