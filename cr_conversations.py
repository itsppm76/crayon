"""Owner-bound web conversation threads. Shared facts stay shared; turn history does not."""
from contextvars import ContextVar
import secrets
import cr_db as db
current=ContextVar('crayon_conversation',default=None)
def init():
    db.q('CREATE TABLE IF NOT EXISTS web_conversations(user_id BIGINT NOT NULL,id TEXT NOT NULL,title TEXT NOT NULL,created_at TIMESTAMPTZ DEFAULT now(),PRIMARY KEY(user_id,id))',fetch='none')
    db.q('ALTER TABLE messages ADD COLUMN IF NOT EXISTS conversation_id TEXT',fetch='none')
    db.q('ALTER TABLE web_requests ADD COLUMN IF NOT EXISTS conversation_id TEXT',fetch='none')
def create(uid,title):
    if not isinstance(title,str) or not 1<=len(title.strip())<=80:raise ValueError('Use a title between 1 and 80 characters.')
    ident=secrets.token_urlsafe(32)
    db.q('INSERT INTO web_conversations(user_id,id,title) VALUES(%s,%s,%s)',(uid,ident,title.strip()),'none')
    return {'id':ident,'title':title.strip()}
def require(uid,ident):
    import cr_web_auth as A
    if not isinstance(ident,str) or not A.PATTERN.fullmatch(ident):raise ValueError('Invalid conversation.')
    row=db.q('SELECT id,title FROM web_conversations WHERE user_id=%s AND id=%s',(uid,ident),'one')
    if not row:raise ValueError('Conversation not found in your account.')
    return row
def list_for(uid):
    return db.q('SELECT id,title,created_at FROM web_conversations WHERE user_id=%s ORDER BY created_at DESC LIMIT 50',(uid,))
def history(uid,ident):
    require(uid,ident)
    rows=db.q('SELECT id,role,content,ts FROM messages WHERE user_id=%s AND conversation_id=%s ORDER BY id DESC LIMIT 100',(uid,ident))
    return {'messages':[{'id':str(r['id']),'role':r['role'],'text':r['content'],'time':str(r['ts'])} for r in reversed(rows)]}
