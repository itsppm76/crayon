"""HTTP surface for Pages frontend. Exact origins, short-lived server sessions."""
import html
import json
import secrets
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, urlsplit
import cr_config as C
import cr_web_auth as A
import cr_web_app as W


def reply(h, status, body, ctype='application/json', cors=False, extra=None):
    data = json.dumps(body).encode() if ctype == 'application/json' else body.encode()
    h.send_response(status)
    h.send_header('Content-Type',ctype)
    h.send_header('Content-Length',str(len(data)))
    h.send_header('Cache-Control','no-store')
    h.send_header('Referrer-Policy','no-referrer')
    h.send_header('X-Content-Type-Options','nosniff')
    h.send_header('X-Frame-Options','DENY')
    if cors:
        h.send_header('Access-Control-Allow-Origin',A.origin())
        h.send_header('Vary','Origin')
    for k,v in (extra or {}).items(): h.send_header(k,v)
    h.end_headers()
    h.wfile.write(data)


def handle(h, method, raw=b''):
    p=urlsplit(h.path)
    if not p.path.startswith('/web/'):
        return False
    origin=h.headers.get('Origin')
    try:
        if method=='GET' and p.path=='/web/auth/start':
            q=parse_qs(p.query)
            if set(q)!={'challenge'} or len(q['challenge'])!=1: raise ValueError('Invalid login start.')
            url,cookie=A.begin(q['challenge'][0])
            reply(h,302,'','text/plain',extra={'Location':url,'Set-Cookie':'crayon_oidc='+cookie+'; Path=/web/auth; Max-Age=300; Secure; HttpOnly; SameSite=Lax'})
            return True
        if method=='GET' and p.path=='/web/auth/callback':
            q=parse_qs(p.query)
            cookies=SimpleCookie(h.headers.get('Cookie',''))
            if 'error' in q: raise A.AuthError('Telegram login was cancelled.')
            if set(q)!={'code','state'} or any(len(v)!=1 for v in q.values()): raise A.AuthError('Invalid login response.')
            code=A.callback(q['state'][0],q['code'][0],cookies['crayon_oidc'].value if 'crayon_oidc' in cookies else '')
            nonce=secrets.token_urlsafe(24)
            body='<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>Crayon login</title><p>Login checked. Return to the original Crayon tab to finish signing in.</p><script nonce="'+nonce+'">if(window.opener){window.opener.postMessage('+json.dumps({'type':'crayon-login','code':code})+','+json.dumps(A.origin())+');window.close();}</script>'
            reply(h,200,body,'text/html',extra={'Set-Cookie':'crayon_oidc=; Path=/web/auth; Max-Age=0; Secure; HttpOnly; SameSite=Lax', 'Content-Security-Policy':"default-src 'none'; script-src 'nonce-"+nonce+"'; base-uri 'none'; frame-ancestors 'none'"})
            return True
        # Same-origin public status has no private contents. Cross-origin API requires exact origin.
        if origin != A.origin():
            reply(h,403,{'error':'Origin not allowed.'})
            return True
        if method=='OPTIONS':
            reply(h,204,'','text/plain',True,{'Access-Control-Allow-Methods':'GET, POST, OPTIONS','Access-Control-Allow-Headers':'Authorization, Content-Type','Access-Control-Max-Age':'600'})
            return True
        if method=='GET' and p.path=='/web/status':
            reply(h,200,{'stage':'private foundation','login_configured':A.configured(),'rooms':False,'external_actions':False,'uploads':False,'computer':False},cors=True)
            return True
        if method=='POST':
            if h.headers.get('Content-Type','').split(';')[0]!='application/json' or len(raw)>40000:
                raise ValueError('JSON body required, maximum 40 KB.')
            body=json.loads(raw)
            if not isinstance(body,dict): raise ValueError('Invalid JSON body.')
        else: body={}
        if method=='POST' and p.path=='/web/session':
            if set(body)!={'code','verifier'}: raise ValueError('Invalid exchange.')
            reply(h,200,A.exchange(body['code'],body['verifier']),cors=True)
            return True
        if method=='POST' and p.path=='/web/login-poll':
            if set(body)!={'verifier'}: raise ValueError('Invalid login poll.')
            reply(h,200,A.poll_login(body['verifier']),cors=True)
            return True
        user=A.session(h.headers.get('Authorization',''))
        if method=='POST' and p.path=='/web/logout':
            A.logout(h.headers.get('Authorization',''))
            reply(h,200,{'ok':True},cors=True)
        elif method=='GET' and p.path=='/web/me':
            reply(h,200,{'id':user['user_id'],'name':user['name']},cors=True)
        elif method=='GET' and p.path=='/web/history':
            reply(h,200,{'messages':W.history(user['user_id'])},cors=True)
        elif method=='GET' and p.path=='/web/activity':
            reply(h,200,{'activity':W.activity(user['user_id'])},cors=True)
        elif method=='POST' and p.path=='/web/chat':
            reply(h,202,W.submit(user,body),cors=True)
        elif method=='GET' and p.path=='/web/result':
            q=parse_qs(p.query)
            if set(q)!={'id'} or len(q['id'])!=1: raise ValueError('Invalid result request.')
            reply(h,200,W.result(user['user_id'],q['id'][0]),cors=True)
        else:
            reply(h,404,{'error':'Web feature not enabled.'},cors=True)
    except A.AuthError as e:
        reply(h,401,{'error':str(e)},cors=origin==A.origin())
    except (UnicodeError, json.JSONDecodeError):
        reply(h,503,{'error':'Telegram response could not be checked. Start login again.'},cors=origin==A.origin())
    except ValueError as e:
        reply(h,400,{'error':str(e)[:200]},cors=origin==A.origin())
    except Exception:
        reply(h,503,{'error':'Web request stopped. No outcome confirmed.'},cors=origin==A.origin())
    return True
