import io
import json
from urllib.parse import parse_qs, urlsplit
import pytest
from cryptography.fernet import Fernet
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
import cr_web_auth as A
import cr_web_http as H
import cr_web_app as W
import cr_channel
import cr_tools as T

@pytest.fixture
def config(monkeypatch):
    monkeypatch.setenv('TELEGRAM_OIDC_CLIENT_ID','123456')
    monkeypatch.setenv('TELEGRAM_OIDC_CLIENT_SECRET','private-client-secret')
    monkeypatch.setenv('CRAYON_WEB_ENCRYPTION_KEY',Fernet.generate_key().decode())
    monkeypatch.setattr(A.db,'available',lambda:True)
    return monkeypatch

class Handler:
    def __init__(self,path,headers=None):self.path=path;self.headers=headers or {};self.wfile=io.BytesIO();self.out={};self.code=None
    def send_response(self,n):self.code=n
    def send_header(self,k,v):self.out[k]=v
    def end_headers(self):pass

def test_login_disabled_no_fake_auth(monkeypatch):
    monkeypatch.delenv('TELEGRAM_OIDC_CLIENT_ID',raising=False)
    with pytest.raises(A.AuthError):A.begin('a'*43)

def test_start_narrow_scopes_state_nonce_pkce(config):
    calls=[];config.setattr(A.db,'q',lambda *a,**kw:calls.append((a,kw)))
    url,cookie=A.begin('a'*43);q=parse_qs(urlsplit(url).query)
    assert q['scope']==['openid profile'] and q['code_challenge_method']==['S256']
    assert q['nonce'] and q['state'] and 'private-client-secret' not in url
    assert calls[-1][0][1][1]==A.digest(cookie)
    decoded=json.loads(A._cipher().decrypt(calls[-1][0][1][3].encode()))
    assert q['code_challenge']==[A.challenge(decoded['verifier'])]

@pytest.mark.parametrize('bad',['http://itsppm76.github.io','https://itsppm76.github.io/crayon','https://evil.test/path','https://u:p@evil.test','https://evil.test:444'])
def test_bad_origin_configuration(monkeypatch,bad):
    monkeypatch.setenv('CRAYON_WEB_ORIGIN',bad)
    with pytest.raises(A.AuthError):A.origin()

def test_bad_login_challenge(config):
    with pytest.raises(A.AuthError):A.begin('not a challenge')

def test_callback_browser_bound_atomic_consumption(config):
    captured=[]
    config.setattr(A.db,'q',lambda sql,p=(),fetch='all':captured.append((sql,p)) or None)
    with pytest.raises(A.AuthError):A.callback('a'*43,'code','b'*43)
    assert captured[0][1]==(A.digest('a'*43),A.digest('b'*43))
    assert 'DELETE' in captured[0][0] and 'expires_at>now()' in captured[0][0]

def test_exchange_requires_verifier_one_use(config):
    captured=[]
    config.setattr(A.db,'q',lambda sql,p=(),fetch='all':captured.append((sql,p)) or None)
    with pytest.raises(A.AuthError):A.exchange('a'*43,'b'*43)
    assert captured[0][1]==(A.digest('a'*43),A.challenge('b'*43))
    assert 'DELETE' in captured[0][0]

def test_exchange_stores_only_hashed_token(config):
    calls=[]
    def q(sql,p=(),fetch='all'):
        calls.append((sql,p));return {'user_id':17,'name':'Person'} if sql.startswith('DELETE FROM web_login_codes WHERE code_hash') else None
    config.setattr(A.db,'q',q);config.setattr(A.db,'audit',lambda *a:None)
    r=A.exchange('a'*43,'b'*43)
    stored=next(p for sql,p in calls if sql.startswith('INSERT INTO web_sessions'))
    assert stored[0]==A.digest(r['token']) and stored[0]!=r['token']
    assert r['user']['id']==17 and r['expires_in']==1800

def test_session_never_takes_client_uid(config):
    calls=[];config.setattr(A.db,'q',lambda sql,p=(),fetch='all':calls.append((sql,p)) or {'user_id':17,'name':'N'})
    assert A.session('Bearer '+'b'*43)['user_id']==17
    assert calls[0][1]==(A.digest('b'*43),)
    for h in ('','17','Bearer x'):
        with pytest.raises(A.AuthError):A.session(h)

def test_jwt_profile_id_not_sub(config):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    config.setattr(A.jwt.PyJWKClient,'get_signing_key_from_jwt',lambda self,t:type('K',(),{'key':key.public_key()})())
    import time
    claims={'iss':A.ISSUER,'aud':'123456','sub':'987987987','id':17,'iat':int(time.time()),'exp':int(time.time())+100,'nonce':'nonce','name':'N'}
    t=jwt.encode(claims,key,algorithm='RS256')
    assert A.validate_id_token(t,'nonce')==(17,'N')
    assert A.validate_id_token(jwt.encode({**claims,'id':'17'},key,algorithm='RS256'),'nonce')==(17,'N')
    with pytest.raises(A.AuthError):A.validate_id_token(t,'wrong')
    for changed in ({'aud':'wrong'},{'iss':'evil'},{'exp':1},{'iat':1},{'id':True},{'id':'17x'},{'id':17.0},{'id':'-17'},{'id':'017'}):
        with pytest.raises((A.AuthError,jwt.InvalidTokenError)):
            A.validate_id_token(jwt.encode({**claims,**changed},key,algorithm='RS256'),'nonce')
    with pytest.raises(jwt.InvalidAlgorithmError):
        A.validate_id_token(jwt.encode(claims,'x'*32,algorithm='HS256'),'nonce')

def test_cors_no_wildcard_or_credentials(config):
    h=Handler('/web/status',{'Origin':'https://evil.test'})
    H.handle(h,'GET');assert h.code==403 and 'Access-Control-Allow-Origin' not in h.out
    h=Handler('/web/status',{'Origin':A.origin()})
    H.handle(h,'GET');assert h.code==200 and h.out['Access-Control-Allow-Origin']==A.origin()
    assert 'Access-Control-Allow-Credentials' not in h.out

def test_preflight(config):
    h=Handler('/web/chat',{'Origin':A.origin()});H.handle(h,'OPTIONS')
    assert h.code==204 and h.out['Access-Control-Allow-Headers']=='Authorization, Content-Type'

def test_private_routes_require_session(config):
    config.setattr(A.db,'q',lambda *a,**kw:None)
    for path in ('/web/history','/web/activity','/web/me','/web/result?id='+'a'*43):
        h=Handler(path,{'Origin':A.origin()});H.handle(h,'GET');assert h.code==401

def test_history_scope_from_session(config):
    calls=[];config.setattr(A,'session',lambda h:{'user_id':17,'name':'N'})
    config.setattr(W,'history',lambda uid:calls.append(uid) or [])
    h=Handler('/web/history?uid=99',{'Origin':A.origin(),'Authorization':'Bearer x'})
    H.handle(h,'GET');assert calls==[17] and h.code==200

def test_chat_cannot_supply_uid(config):
    config.setattr(A,'session',lambda h:{'user_id':17,'name':'N'})
    h=Handler('/web/chat',{'Origin':A.origin(),'Content-Type':'application/json'})
    H.handle(h,'POST',json.dumps({'message':'Hi','request_id':'a'*43,'uid':99}).encode());assert h.code==400

def test_web_tools_enforced_even_if_model_requests(config):
    mark=cr_channel.channel.set('web')
    try:
        names=[x['name'] for x in T.declarations()[0]['functionDeclarations']]
        assert 'remember' in names and 'create_task' in names
        for name in ('computer_browse','computer_task','schedule_job','forget'):
            assert name not in names and not T.run(name,{}, {'uid':17,'chat_id':17})['ok']
    finally:cr_channel.channel.reset(mark)
    assert 'computer_browse' in [x['name'] for x in T.declarations()[0]['functionDeclarations']]

def test_secret_rejected_before_storage(config):
    config.setattr(W.db,'q',lambda *a,**k:pytest.fail('secret must not be stored'))
    with pytest.raises(ValueError):W.submit({'user_id':17,'name':'N'},{'message':'password: veryprivate123','request_id':'a'*43})

def test_duplicate_not_rerun(config):
    config.setattr(W.db,'q',lambda *a,**k:{'state':'done'})
    config.setattr(W.POOL,'submit',lambda *a:pytest.fail('no rerun'))
    assert W.submit({'user_id':17,'name':'N'},{'message':'hello','request_id':'a'*43})['state']=='done'

def test_result_cross_user_fail_closed(config):
    calls=[];config.setattr(W.db,'q',lambda sql,p=(),fetch='all':calls.append(p) or None)
    with pytest.raises(ValueError):W.result(17,'a'*43)
    assert calls==[(17,'a'*43)]

def test_artifacts_bounded_plain_output():
    o=W.WebOut();o.send(17,'<script>alert(1)</script>')
    assert o.items[0]['text'].startswith('<script>') # frontend renders with textContent, not HTML
    o.artifact(17,{'filename':'../../a.csv','mime':'text/csv','data':b'x,y'})
    assert o.items[1]['name']=='a.csv'
    with pytest.raises(ValueError):o.artifact(17,{'filename':'big','mime':'text/plain','data':b'x'*2000001})

def test_dispatch_does_not_use_telegram_confirmation(config):
    import cr_memory as M,cr_agent as Brain
    config.setattr(M,'touch_user',lambda *a:None)
    config.setattr(Brain,'respond',lambda *a,**k:pytest.fail('must not run model/confirmation'))
    for s in ('yes','send it','connect Google','read my inbox','forget name','computer calculate 2+2'):
        assert W.dispatch(17,'N',s)[0]['kind']=='text'

def test_frontend_no_tokens_in_persistent_storage():
    from pathlib import Path
    s=Path('docs/app.js').read_text()
    assert 'localStorage' not in s and 'sessionStorage' not in s
    assert "e.origin!==API||e.source!==popup" in s
    assert '.innerHTML' not in s
    assert 'session_id' not in s


def test_jwks_gzip_decoded_before_json(config):
    import gzip, httpx
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    payload = {'keys': [json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))]}
    client = httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(
        200, headers={'Content-Encoding':'gzip','Content-Type':'application/json'},
        content=gzip.compress(json.dumps(payload).encode()))))
    config.setattr(A.httpx,'get',lambda *args,**kwargs:client.get('https://oauth.telegram.org/.well-known/jwks.json'))
    assert A.TelegramJWKClient(A.ISSUER+'/.well-known/jwks.json').fetch_data()==payload


def test_jwks_decode_errors_not_exposed(config):
    class Bad:
        def raise_for_status(self): pass
        def json(self): raise UnicodeDecodeError('utf-8',b'\x1f\x8b',1,2,'invalid start byte')
    config.setattr(A.httpx,'get',lambda *a,**k:Bad())
    with pytest.raises(A.AuthError,match='signing keys could not be checked'):
        A.TelegramJWKClient(A.ISSUER+'/.well-known/jwks.json').fetch_data()


def test_provider_decode_error_safe_http(config):
    def fail(*a): raise UnicodeDecodeError('utf-8',b'\x1f\x8b',1,2,'invalid start byte')
    config.setattr(A,'callback',fail)
    h=Handler('/web/auth/callback?code=x&state=y')
    H.handle(h,'GET')
    assert h.code==503
    assert b'utf-8' not in h.wfile.getvalue() and b'Start login again' in h.wfile.getvalue()
