import json
import pytest
from cryptography.fernet import Fernet
import cr_web_actions as X
import cr_web_auth as A
import cr_web_http as H
from test_web_app import Handler

@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv('CRAYON_WEB_ENCRYPTION_KEY',Fernet.generate_key().decode())
    monkeypatch.setattr(X.db,'q',lambda *a,**k:None)
    return monkeypatch

def test_web_preview_only_no_send(config):
    calls=[]
    config.setattr(X.G,'make_draft',lambda uid,f,structured,channel:{'id':'draft','hash':'hash','text':'From: own@example.com\nTo: user@example.com\nExact body'})
    config.setattr(X.G,'send_draft',lambda *a:pytest.fail('preview cannot send'))
    config.setattr(X.db,'q',lambda sql,p=(),fetch='all':calls.append((sql,p)))
    r=X.preview(17,'Bearer '+'a'*43,{'kind':'email','fields':dict(to=['user@example.com'],cc=[],bcc=[],subject='Hi',body='Body')})
    saved=next(p for sql,p in calls if sql.startswith('INSERT'))
    assert saved[1:3]==(17,A.digest('a'*43)) and saved[4]==r['hash']
    assert 'Exact body' in r['text'] and 'Exact body' not in saved[3]

def test_confirmation_wrong_session_cannot_send(config):
    calls=[]
    config.setattr(X.db,'q',lambda sql,p=(),fetch='all':calls.append((sql,p)) or None)
    config.setattr(X.G,'send_draft',lambda *a:pytest.fail('no send'))
    with pytest.raises(ValueError):X.confirm(17,'Bearer '+'b'*43,{'review_id':'review','hash':'hash','decision':'confirm'})
    claim=next(p for sql,p in calls if sql.startswith('UPDATE'))
    assert claim==('review',17,A.digest('b'*43),'hash')

def test_confirmation_exact_one_use(config):
    data={'kind':'email','payload':{'id':'draft','hash':'short'},'text':'Exact recipients and body'}
    import hashlib
    digest=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
    row={'encrypted':A._cipher().encrypt(json.dumps(data).encode()).decode(),'content_hash':digest}
    claims=[];sent=[]
    def q(sql,p=(),fetch='all'):
        if sql.startswith('UPDATE web_action_reviews SET status=') and "'claimed'" in sql:
            claims.append(p);return row if len(claims)==1 else None
    config.setattr(X.db,'q',q);config.setattr(X.G,'send_draft',lambda *a,**kw:sent.append(a) or 'Sent')
    body={'review_id':'r','hash':digest,'decision':'confirm'}
    assert X.confirm(17,'Bearer '+'a'*43,body)['text']=='Sent'
    with pytest.raises(ValueError):X.confirm(17,'Bearer '+'a'*43,body)
    assert sent==[(17,'draft','short')]

def test_private_reads_no_model_or_history(config):
    config.setattr(X.G,'inbox',lambda uid,q:'private result')
    r=X.read(17,{'kind':'inbox','fields':{'query':'newer_than:1d'}})
    assert r['text']=='private result' and not r['stored_in_history'] and not r['sent_to_ai']
    with pytest.raises(ValueError):X.read(17,{'kind':'inbox','fields':{'query':'','uid':99}})
    config.setattr(X.G,'calendar',lambda uid:'calendar_'+str(uid))
    assert X.read(17,{'kind':'calendar','fields':{}})['text']=='calendar_17'

def test_actions_require_authenticated_exact_origin(config):
    config.setattr(A,'session',lambda *a:(_ for _ in ()).throw(A.AuthError('Login first')))
    for path in ['/web/action-preview','/web/action-confirm','/web/private-read','/web/connect']:
        h=Handler(path,{'Origin':A.origin(),'Content-Type':'application/json'})
        H.handle(h,'POST',b'{}');assert h.code==401
        h=Handler(path,{'Origin':'https://evil.test','Content-Type':'application/json'})
        H.handle(h,'POST',b'{}');assert h.code==403


def test_google_send_claim_includes_channel(config):
    calls=[]
    config.setattr(X.db,'kv_get',lambda *a:None)
    config.setattr(X.db,'q',lambda sql,p=(),fetch='all':calls.append((sql,p)) or None)
    with pytest.raises(X.G.GoogleError):X.G.send_draft(17,'id','hash',channel='web')
    assert calls[0][1]==('id',17,'web','hash') and 'origin=%s' in calls[0][0]


def test_connections_no_workspace_returns_none(config):
    import cr_connections as C
    config.setattr(X.G,'status',lambda uid:{'email':'own@example.com'})
    config.setattr(C,'status',lambda uid,p:None)
    assert X.connections(17)['workspace'] is None


def test_telegram_draft_lookup_excludes_web(config):
    calls=[]
    config.setattr(X.db,'q',lambda sql,p=(),fetch='all':calls.append(sql) or [])
    with pytest.raises(X.G.GoogleError):X.G.current_draft(17)
    assert "origin='telegram'" in calls[0]
