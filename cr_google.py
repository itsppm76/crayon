"""Per-user Google OAuth foundation. Disabled until explicitly configured."""
import hashlib
import json
import secrets
import re
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet

import cr_config as C
import cr_db as db

SCOPES = ["openid", "email", "https://www.googleapis.com/auth/gmail.readonly",
          "https://www.googleapis.com/auth/calendar.events.readonly"]

class GoogleError(Exception):
    pass


def configured():
    return all(C.env(k) for k in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_TOKEN_ENCRYPTION_KEY"))


def _cipher():
    try:
        return Fernet(C.env("GOOGLE_TOKEN_ENCRYPTION_KEY").encode())
    except Exception:
        raise GoogleError("Google connection is not configured safely") from None


def encrypt(uid, token):
    # User binding is checked after decrypt, even if a row is misplaced.
    return _cipher().encrypt(json.dumps({"uid":int(uid),"tokens":token}).encode()).decode()


def decrypt(uid, blob):
    try:
        data=json.loads(_cipher().decrypt(blob.encode()))
        if data["uid"] != int(uid):
            raise ValueError()
        return data["tokens"]
    except Exception:
        raise GoogleError("Google credential binding failed") from None


def init():
    db.q("""CREATE TABLE IF NOT EXISTS google_connections(
        user_id BIGINT PRIMARY KEY, email TEXT NOT NULL, encrypted_tokens TEXT NOT NULL,
        connected_at TIMESTAMPTZ DEFAULT now())""",fetch="none")
    db.q("""CREATE TABLE IF NOT EXISTS google_oauth_states(
        state_hash TEXT PRIMARY KEY, user_id BIGINT NOT NULL, expires_at TIMESTAMPTZ NOT NULL,
        used BOOLEAN DEFAULT false)""",fetch="none")


def redirect_uri():
    return C.PUBLIC_URL.rstrip("/") + "/google/callback"


def begin(uid):
    if not configured():
        raise GoogleError("Google setup is not active yet")
    if int(uid)<=0:
        raise GoogleError("A real private Telegram user is required")
    init()
    state=secrets.token_urlsafe(32)
    hashed=hashlib.sha256(state.encode()).hexdigest()
    db.q("DELETE FROM google_oauth_states WHERE expires_at<now()",fetch="none")
    db.q("INSERT INTO google_oauth_states(state_hash,user_id,expires_at) VALUES(%s,%s,now()+interval '10 minutes')",(hashed,uid),"none")
    return "https://accounts.google.com/o/oauth2/v2/auth?"+urlencode({
        "client_id":C.env("GOOGLE_CLIENT_ID"),"redirect_uri":redirect_uri(),"response_type":"code",
        "scope":" ".join(SCOPES),"access_type":"offline","prompt":"consent","state":state})


def complete(state, code):
    if not configured() or len(state)>200 or len(code)>3000:
        raise GoogleError("Invalid or unavailable Google connection")
    hashed=hashlib.sha256(state.encode()).hexdigest()
    row=db.q("UPDATE google_oauth_states SET used=true WHERE state_hash=%s AND used=false AND expires_at>now() RETURNING user_id",(hashed,),"one")
    if not row:
        raise GoogleError("Connection link expired or already used; start again in Telegram")
    uid=row["user_id"]
    with httpx.Client(timeout=20) as client:
        r=client.post("https://oauth2.googleapis.com/token",data={"client_id":C.env("GOOGLE_CLIENT_ID"),
            "client_secret":C.env("GOOGLE_CLIENT_SECRET"),"code":code,"grant_type":"authorization_code","redirect_uri":redirect_uri()})
        if r.status_code!=200:
            raise GoogleError("Google did not complete the connection")
        tokens=r.json()
        granted=set(tokens.get("scope","").split())
        if not set(SCOPES).issubset(granted) or not tokens.get("refresh_token"):
            raise GoogleError("Required read-only permissions or refresh token were not granted")
        profile=client.get("https://openidconnect.googleapis.com/v1/userinfo",headers={"Authorization":"Bearer "+tokens["access_token"]})
        if profile.status_code!=200 or not profile.json().get("email_verified"):
            raise GoogleError("Could not verify the connected Google account")
        email=profile.json()["email"]
    db.q("INSERT INTO google_connections(user_id,email,encrypted_tokens) VALUES(%s,%s,%s) ON CONFLICT(user_id) DO UPDATE SET email=EXCLUDED.email,encrypted_tokens=EXCLUDED.encrypted_tokens,connected_at=now()",(uid,email,encrypt(uid,tokens)),"none")
    return {"user_id":uid,"email":email}


def _access(uid):
    if not configured():
        raise GoogleError("Google setup is not active yet")
    row=db.q("SELECT encrypted_tokens FROM google_connections WHERE user_id=%s",(uid,),"one")
    if not row:
        raise GoogleError("Connect your own Google account first")
    tokens=decrypt(uid,row["encrypted_tokens"])
    with httpx.Client(timeout=20) as client:
        r=client.post("https://oauth2.googleapis.com/token",data={"client_id":C.env("GOOGLE_CLIENT_ID"),"client_secret":C.env("GOOGLE_CLIENT_SECRET"),"refresh_token":tokens["refresh_token"],"grant_type":"refresh_token"})
    if r.status_code!=200:
        raise GoogleError("Google access expired or was revoked; reconnect your account")
    return r.json()["access_token"]


def request(uid, url, params=None):
    # Read-only allowlist. Sending/draft endpoints cannot be reached through this function.
    if not (re.fullmatch(r"https://gmail\.googleapis\.com/gmail/v1/users/me/messages(?:/[A-Za-z0-9_-]+)?",url) and not url.endswith("/send") or
            url == "https://www.googleapis.com/calendar/v3/calendars/primary/events"):
        raise GoogleError("That Google operation is not allowed")
    # Fixed conservative cap, and no retry or quota increase.
    n=db.q("SELECT count(*) AS n FROM audit WHERE user_id=%s AND event='google_read' AND ts>now()-interval '24 hours'",(uid,),"one")["n"]
    if n>=100:
        raise GoogleError("Daily Google request limit reached")
    token=_access(uid)
    db.audit(uid,"google_read")
    with httpx.Client(timeout=20) as client:
        r=client.get(url,params=params or {},headers={"Authorization":"Bearer "+token})
    if r.status_code!=200:
        raise GoogleError("Google read failed or quota/permissions blocked it")
    return r.json()


def disconnect(uid):
    row=db.q("SELECT encrypted_tokens FROM google_connections WHERE user_id=%s",(uid,),"one")
    revoked=True
    if row:
        try:
            token=decrypt(uid,row["encrypted_tokens"])["refresh_token"]
            with httpx.Client(timeout=20) as client:
                revoked=client.post("https://oauth2.googleapis.com/revoke",data={"token":token}).status_code==200
        except Exception:
            revoked=False
    db.q("DELETE FROM google_connections WHERE user_id=%s",(uid,),"none")
    db.q("DELETE FROM google_oauth_states WHERE user_id=%s",(uid,),"none")
    return {"deleted":db.q("SELECT 1 FROM google_connections WHERE user_id=%s",(uid,),"one") is None,"revoked":revoked}
