import pytest
from cryptography.fernet import Fernet
import cr_google as G


def test_encrypted_token_bound_to_user(monkeypatch):
    key=Fernet.generate_key().decode()
    monkeypatch.setenv('GOOGLE_TOKEN_ENCRYPTION_KEY',key)
    token={'refresh_token':'synthetic-secret'}
    blob=G.encrypt(11,token)
    assert 'synthetic-secret' not in blob
    assert G.decrypt(11,blob)==token
    with pytest.raises(G.GoogleError):
        G.decrypt(12,blob)
    with pytest.raises(G.GoogleError):
        G.decrypt(11,blob[:-3]+'bad')


def test_oauth_off_without_secrets(monkeypatch):
    monkeypatch.delenv('GOOGLE_CLIENT_ID',raising=False)
    assert not G.configured()
    with pytest.raises(G.GoogleError):
        G.begin(11)


def test_no_write_endpoint():
    with pytest.raises(G.GoogleError):
        G.request(11,'https://gmail.googleapis.com/gmail/v1/users/me/messages/send')


def test_oauth_state_replay_fails_before_token_exchange(monkeypatch):
    monkeypatch.setattr(G,'configured',lambda:True)
    monkeypatch.setattr(G.db,'q',lambda *a,**k:None)
    with pytest.raises(G.GoogleError,match='expired or already used'):
        G.complete('used-state','fake-code')


def test_no_other_users_token_read(monkeypatch):
    seen=[]
    def q(sql,params=(),fetch='all'):
        seen.append(params)
        return None
    monkeypatch.setattr(G,'configured',lambda:True)
    monkeypatch.setattr(G.db,'q',q)
    with pytest.raises(G.GoogleError,match='Connect your own'):
        G._access(22)
    assert seen==[(22,)]


def test_draft_is_review_only(monkeypatch):
    monkeypatch.setattr(G,'status',lambda uid:{'email':'owner@example.com'})
    monkeypatch.setattr(G,'encrypt',lambda uid,data:'encrypted')
    rows=[]
    monkeypatch.setattr(G.db,'q',lambda *a,**kw:rows.append(a))
    out=G.make_draft(11,'sam@example.com\nMeeting\nCan we meet Friday?')
    assert 'Draft only, not sent' in out and 'owner@example.com' in out and 'sam@example.com' in out
    assert '/email_send ' in out and 'Attachments: none' in out
    assert len(rows)==3


def test_draft_rejects_header_injection(monkeypatch):
    monkeypatch.setattr(G,'status',lambda uid:{'email':'owner@example.com'})
    monkeypatch.setattr(G.db,'q',lambda *a,**kw:None)
    with pytest.raises(G.GoogleError):G.make_draft(11,'sam@example.com,bad@example.com\nSubject\nBody')


def test_send_cross_user_rejected(monkeypatch):
    seen=[]
    def q(sql,params=(),fetch='all'):
        seen.append(params)
        return None
    monkeypatch.setattr(G.db,'q',q)
    with pytest.raises(G.GoogleError):G.send_draft(22,'draftid','hash')
    assert seen==[('draftid',22,'hash')]


def test_draft_hash_tampering_fails_closed(monkeypatch):
    def q(sql,params=(),fetch='all'):
        if sql.startswith('UPDATE google_email_drafts SET status=\'sending\''):
            return {'encrypted_content':'bad','content_hash':'does-not-match'}
    monkeypatch.setattr(G.db,'q',q)
    monkeypatch.setattr(G,'decrypt',lambda *a:{'from':'a@b.com','to':'x@y.com','subject':'Changed','body':'test'})
    monkeypatch.setattr(G,'_access',lambda *a:pytest.fail('network allowed after tamper'))
    with pytest.raises(G.GoogleError):G.send_draft(22,'draftid','hash')


def test_send_timeout_never_retries(monkeypatch):
    import hashlib,json
    content={'from':'owner@example.com','to':'sam@example.com','subject':'Test','body':'Synthetic only'}
    digest=hashlib.sha256(json.dumps(content,sort_keys=True).encode()).hexdigest()
    updates=[]
    def q(sql,params=(),fetch='all'):
        updates.append(sql)
        if "RETURNING encrypted_content" in sql:return {'encrypted_content':'test','content_hash':digest}
    monkeypatch.setattr(G.db,'q',q)
    monkeypatch.setattr(G,'decrypt',lambda *a:content)
    monkeypatch.setattr(G,'status',lambda *a:{'email':'owner@example.com'})
    monkeypatch.setattr(G,'_access',lambda *a:'fake')
    class Client:
        calls=0
        def __init__(self,**kw):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def post(self,*a,**kw):
            Client.calls+=1
            raise TimeoutError()
    monkeypatch.setattr(G.httpx,'Client',Client)
    with pytest.raises(G.GoogleError,match='uncertain'):G.send_draft(22,'id',digest[:12])
    assert Client.calls==1
    assert any("status='uncertain'" in s for s in updates)


def test_google_group_read_blocked(monkeypatch):
    import cr_telegram as T
    monkeypatch.setattr(T.db,'audit',lambda *a:None)
    monkeypatch.setattr(G,'request',lambda *a:pytest.fail('group google read'))
    out=T.CaptureOut()
    T._handle_text(22,-123,'Test','/gmail',1,out)
    assert 'private chat' in out.sent[0]['text']


def test_draft_single_line_review(monkeypatch):
    monkeypatch.setattr(G,'status',lambda uid:{'email':'owner@example.com'})
    monkeypatch.setattr(G,'encrypt',lambda uid,data:'encrypted')
    monkeypatch.setattr(G.db,'q',lambda *a,**kw:None)
    out=G.make_draft(11,'owner@example.com | Review only | Do not send this.')
    assert 'Draft only, not sent' in out and 'Subject: Review only' in out


def test_email_button_user_binding(monkeypatch):
    import cr_telegram as T
    monkeypatch.setattr(T,'api',lambda *a,**kw:None)
    monkeypatch.setattr(G,'send_draft',lambda *a:pytest.fail('cross-user callback send'))
    out=T.CaptureOut()
    T.handle_callback({'id':'c','from':{'id':22},'message':{'chat':{'id':33}},'data':'email_send:id:hash'},out)
    assert not out.sent


def test_review_button_exact_bound_fields(monkeypatch):
    import cr_telegram as T
    monkeypatch.setattr(T,'api',lambda *a,**kw:None)
    seen=[]
    monkeypatch.setattr(G,'send_draft',lambda *a:seen.append(a) or 'Sent test (mock)')
    out=T.CaptureOut()
    T.handle_callback({'id':'c','from':{'id':22},'message':{'chat':{'id':22}},'data':'email_send:id:hash'},out)
    assert seen==[(22,'id','hash')]
