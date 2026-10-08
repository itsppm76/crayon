import pytest,time
import cr_calendar_draft as K
import cr_mail_watch as W
import cr_google as G

def content():return {'account':'me@example.com','summary':'Study','start':'2099-01-01T10:00:00+05:30','end':'2099-01-01T11:00:00+05:30','timezone':'Asia/Calcutta'}
def test_calendar_validate():
    assert K.validate(content())
    for change in ({'start':'2099-01-01T10:00:00'},{'end':'2099-01-01T09:00:00+05:30'},{'timezone':'America/New_York'},{'attendees':[]}):
        with pytest.raises(G.GoogleError):K.validate({**content(),**change})
def test_calendar_preview_no_network(monkeypatch):
    monkeypatch.setattr(K.db,'q',lambda *a,**kw:None)
    monkeypatch.setattr(K.db,'kv_set',lambda *a:None)
    monkeypatch.setattr(G,'status',lambda *a:{'email':'me@example.com'})
    monkeypatch.setattr(G,'encrypt',lambda u,c:'encrypted')
    monkeypatch.setattr(G,'request',lambda *a:pytest.fail('write while preview'))
    d=K.preview(10,'Study',content()['start'],content()['end'],content()['timezone'])
    assert 'not booked' in d['text'] and 'No attendees' in d['text']
def test_calendar_stale_user_rejected(monkeypatch):
    monkeypatch.setattr(K.db,'q',lambda *a,**kw:None)
    monkeypatch.setattr(K.db,'kv_get',lambda *a:None)
    with pytest.raises(G.GoogleError,match='Review'):K.create(11,'id','hash')
def test_mail_metadata_only_dedup(monkeypatch):
    monkeypatch.setattr(G,'status',lambda *a:{'email':'me@example.com'})
    calls=[]
    def req(uid,url,params):
        calls.append((url,params))
        if url.endswith('/messages'):return {'messages':[{'id':'a'},{'id':'b'}]}
        return {'labelIds':['IMPORTANT'] if url.endswith('a') else [],'payload':{'headers':[{'name':'From','value':'external@example.com'},{'name':'Subject','value':'Deadline' if url.endswith('a') else 'Newsletter'}]}}
    monkeypatch.setattr(G,'request',req)
    state={'email':'me@example.com','since':100,'seen':[]}
    text,state=W.scan(W.OWNER,state)
    assert 'May need attention' in text and 'FYI:' in text
    assert all(p.get('format')=='metadata' for u,p in calls if not u.endswith('/messages'))
    assert W.scan(W.OWNER,state)[0]==''
def test_mail_quiet_and_off(monkeypatch):
    monkeypatch.setattr(W.db,'kv_get',lambda *a:None)
    class Out:
        def send(self,*a):pytest.fail('off sent')
    W.tick(Out())
    monkeypatch.setattr(W.db,'kv_get',lambda *a:{'checked':0})
    monkeypatch.setattr(W.P,'settings',lambda *a:{'quiet_start':21,'quiet_end':9})
    monkeypatch.setattr(W.P.T,'now_local',lambda *a:type('N',(),{'hour':1})())
    monkeypatch.setattr(W,'scan',lambda *a:pytest.fail('quiet read'))
    W.tick(Out())
def test_mail_not_other_user():
    with pytest.raises(G.GoogleError):W.configure(12,12,True)
def test_conflict_and_scope_no_write(monkeypatch):
    import json,hashlib
    c=content();digest=hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest()
    monkeypatch.setattr(K.db,'kv_get',lambda *a:['id',digest[:12]])
    monkeypatch.setattr(K.db,'q',lambda sql,*a,**kw:{'encrypted_content':'x','content_hash':digest} if 'RETURNING encrypted_content' in sql else None)
    monkeypatch.setattr(G,'decrypt',lambda *a:c)
    monkeypatch.setattr(G,'status',lambda *a:{'email':c['account']})
    monkeypatch.setattr(G,'request',lambda *a:{'items':[{'summary':'Busy'}]})
    monkeypatch.setattr(G,'_access',lambda *a:pytest.fail('write conflict'))
    with pytest.raises(G.GoogleError,match='conflicts'):K.create(10,'id',digest[:12])
def test_calendar_preview_route(monkeypatch):
    import cr_google_chat as H,cr_telegram as T
    monkeypatch.setattr(K,'preview',lambda *a:{'id':'id','hash':'hash','text':'Preview only'})
    class Out:
        def __init__(self):self.sent=[]
        def send(self,chat,text,markup=None):self.sent.append({'text':text,'markup':markup})
    out=Out();H.handle(10,10,'/calendar_slot Study | 2099-01-01T10:00:00+05:30 | 2099-01-01T11:00:00+05:30 | Asia/Calcutta',{},out)
    assert out.sent[0]['markup']['inline_keyboard'][0][0]['text']=='Create'
def test_write_scope_only_explicit_oauth(monkeypatch):
    from urllib.parse import urlsplit,parse_qs
    monkeypatch.setattr(G,'configured',lambda:True)
    monkeypatch.setattr(G.db,'q',lambda *a,**kw:{'user_id':10})
    monkeypatch.setattr(G.db,'kv_get',lambda *a:False)
    url=G.authorization_url('a'*43)
    scope=parse_qs(urlsplit(url).query)['scope'][0]
    assert 'calendar.events.readonly' in scope
    monkeypatch.setattr(G.db,'kv_get',lambda *a:True)
    scope=parse_qs(urlsplit(G.authorization_url('a'*43)).query)['scope'][0]
    assert 'calendar.events.readonly' not in scope and 'calendar.events' in scope
def test_calendar_create_readback_exact(monkeypatch):
    import json,hashlib
    c=content();digest=hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest()
    queries=[]
    def q(sql,*a,**kw):
        queries.append(sql)
        return {'encrypted_content':'x','content_hash':digest} if 'RETURNING encrypted_content' in sql else None
    monkeypatch.setattr(K.db,'q',q)
    monkeypatch.setattr(K.db,'kv_get',lambda *a:['a1b2c3',digest[:12]])
    monkeypatch.setattr(G,'decrypt',lambda *a:c)
    monkeypatch.setattr(G,'status',lambda *a:{'email':c['account']})
    monkeypatch.setattr(G,'request',lambda *a:{'items':[]})
    monkeypatch.setattr(G,'_access',lambda *a:'fake')
    class Resp:
        status_code=200
        def __init__(self,data):self.data=data
        def json(self):return self.data
    class Client:
        body=None;posts=0
        def __init__(self,**kw):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def get(self,url,**kw):
            if url.endswith('tokeninfo'):return Resp({'scope':'https://www.googleapis.com/auth/calendar.events'})
            return Resp({**Client.body,'htmlLink':'https://calendar.google.com/test-fixture'})
        def post(self,url,**kw):
            Client.posts+=1;Client.body=kw['json'];assert kw['params']=={'sendUpdates':'none'}
            assert 'attendees' not in Client.body and 'conferenceData' not in Client.body
            return Resp(Client.body)
    monkeypatch.setattr(G.httpx,'Client',Client)
    assert 'read back' in K.create(10,'a1b2c3',digest[:12]);assert Client.posts==1
    assert any(x.startswith('DELETE FROM google_calendar_drafts WHERE id') for x in queries)
