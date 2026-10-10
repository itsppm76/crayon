import json
from unittest.mock import patch
import cr_progress as P
import cr_telegram as T
import cr_tools as Tools

def test_repeated_labels_have_distinct_steps_and_monotonic_sequence():
    token=P.recorded.set([])
    try:
        a=P.emit('Reading a public page');P.emit('Reading a public page','done',step_id=a)
        b=P.emit('Reading a public page');P.emit('Reading a public page','blocked',step_id=b)
        events=P.snapshot()
        assert a!=b and [e['seq'] for e in events]==[1,2,3,4]
        assert [e['id'] for e in events]==[a,a,b,b]
        assert set(events[0])=={'label','state','id','seq'}
    finally:P.recorded.reset(token)

def test_confirmation_is_awaiting_review_not_verified(monkeypatch):
    seen=[];t=P.callback.set(seen.append)
    monkeypatch.setattr(Tools,'_run_inner',lambda *a:{'ok':True,'verified':False,'needs_confirmation':True})
    try:Tools.run('test',{},{});assert seen[-1]['state']=='awaiting_review'
    finally:P.callback.reset(t)

def test_telegram_status_throttled_and_never_updates_after_final(monkeypatch):
    class Out:
        def __init__(self):self.sent=[];self.edits=[]
        def send(self,chat,text,**kw):self.sent.append(text);return len(self.sent)
        def edit_status(self,chat,mid,text):self.edits.append((mid,text));return True
    clock=[1];monkeypatch.setattr(T.time,'monotonic',lambda:clock[0]);out=Out();g=T.ProgressOut(out,1,[])
    g.event({'label':'Reading public source','state':'running'});g.event({'label':'Reading public source','state':'done'})
    assert len(out.sent)==1 and not out.edits
    clock[0]=5;g.event({'label':'Preparing response','state':'running'});assert len(out.edits)==1
    g.send(1,'Final reply');before=(list(out.sent),list(out.edits));g.event({'label':'late','state':'running'})
    assert before==(out.sent,out.edits) and out.sent[-1]=='Final reply'

def test_preview_supersedes_only_owner_session(monkeypatch):
    import cr_web_actions as X
    from test_web_actions import config
    from cryptography.fernet import Fernet
    monkeypatch.setenv('CRAYON_WEB_ENCRYPTION_KEY',Fernet.generate_key().decode());calls=[]
    monkeypatch.setattr(X.db,'q',lambda sql,p=(),fetch='all':calls.append((sql,p)))
    monkeypatch.setattr(X.G,'make_draft',lambda *a,**k:{'id':'d','hash':'h','text':'Exact','html':'Exact','fields':{}})
    fields={'to':['a@example.com'],'cc':[],'bcc':[],'subject':'A','body':'B'}
    r=X.preview(12,'Bearer '+'a'*43,{'kind':'email','fields':fields})
    claim=next((sql,p) for sql,p in calls if 'superseded' in sql)
    assert 'user_id=%s AND session_hash=%s' in claim[0] and claim[1]==(12,X.A.digest('a'*43))
    assert r['review_fields']==fields

def test_unverified_workspace_receipt_is_unknown(monkeypatch):
    import cr_web_actions as X,cr_workspace_create as C,hashlib
    from cryptography.fernet import Fernet
    monkeypatch.setenv('CRAYON_WEB_ENCRYPTION_KEY',Fernet.generate_key().decode())
    data={'kind':'workspace_create','payload':{'kind':'doc','title':'Fixture'},'text':'Exact'}
    digest=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
    row={'encrypted':X.A._cipher().encrypt(json.dumps(data).encode()).decode(),'content_hash':digest}
    monkeypatch.setattr(X.db,'q',lambda sql,*a,**k:row if "status='claimed'" in sql else None)
    monkeypatch.setattr(C,'apply',lambda *a:{'created':True,'content_readback_verified':False,'id':'fixture','note':'Uncertain'})
    result=X.confirm(12,'Bearer '+'a'*43,{'review_id':'r','hash':digest,'decision':'confirm'})
    assert result['state']=='unknown' and result['receipt']['content_readback_verified'] is False
