"""Opt-in hourly metadata-only mail check. No model, body reads or external effects."""
import time,re,json
import cr_db as db
import cr_google as G
import cr_proactive as P
OWNER=1898030949
KEY=lambda uid:'mail_watch_'+str(uid)
def configure(uid,chat,on):
    if uid!=OWNER:raise G.GoogleError('Mail watch beta is owner-only for now.')
    if not on:db.kv_set(KEY(uid),None);return 'Email checks off.'
    row=G.status(uid)
    if not row:raise G.GoogleError('Connect Google first.')
    now=int(time.time())
    db.kv_set(KEY(uid),{'chat':chat,'email':row['email'],'since':now,'checked':now,'seen':[]})
    return 'Email checks on: hourly during your awake hours, from now onward. No replies or calendar changes. Metadata only, never sent to Gemini. Attention uses Google IMPORTANT/starred labels or subject keywords, so it can miss things. Optional mail gets one short FYI. Free-host timing is best-effort.'
def scan(uid,state):
    if G.status(uid).get('email')!=state['email']:raise G.GoogleError('Connected account changed. Turn email checks on again.')
    messages=G.request(uid,'https://gmail.googleapis.com/gmail/v1/users/me/messages',{'q':'in:inbox after:'+str(state['since']),'maxResults':20})
    if len(state.get('seen',[]))>=500:raise G.GoogleError('Mail watch cache full. Re-enable to start a new watch.')
    ids=[m['id'] for m in messages.get('messages',[]) if m['id'] not in state.get('seen',[])][:4]
    attention=[];optional=[]
    for ident in ids:
        item=G.request(uid,'https://gmail.googleapis.com/gmail/v1/users/me/messages/'+ident,{'format':'metadata','metadataHeaders':['From','Subject']})
        h={v['name'].lower():v['value'] for v in item.get('payload',{}).get('headers',[])}
        from cr_safety import redact,clean_text
        subject=redact(clean_text(h.get('subject','(no subject)')).replace('\n',' ')[:130])
        sender=redact(clean_text(h.get('from','unknown sender')).replace('\n',' ')[:100])
        line=sender+': '+subject
        labels=item.get('labelIds',[])
        target=attention if any(x in labels for x in ('IMPORTANT','STARRED')) or re.search(r'\b(deadline|action required|due|overdue|urgent|interview|exam)\b',subject,re.I) else optional
        target.append(line)
    state['seen']=(state.get('seen',[])+ids)[-500:]
    if not ids:return '',state
    lines=['New email metadata (untrusted, no actions taken):']
    if attention:lines+=['May need attention:']+attention
    if optional:lines+=['FYI: '+str(len(optional))+' other new email(s): '+'; '.join(optional)[:250]]
    if messages.get('nextPageToken') or len(messages.get('messages',[]))>len(ids):lines+=['More mail may remain; this check is capped at4 messages.']
    return '\n'.join(lines),state
def tick(out):
    state=db.kv_get(KEY(OWNER),None)
    if not state or state.get('paused') or time.time()-state.get('checked',0)<3600:return
    s=P.settings(OWNER);n=P.T.now_local(OWNER)
    if not P.awake(n.hour,int(s['quiet_start']),int(s['quiet_end'])):return
    with P.mem.user_lock(OWNER):
        state=db.kv_get(KEY(OWNER),None)
        if not state:return
        try:
            text,state=scan(OWNER,state)
            if text:out.send(state['chat'],text)
            state['checked']=int(time.time());db.kv_set(KEY(OWNER),state)
        except G.GoogleError:
            state['checked']=int(time.time());db.kv_set(KEY(OWNER),state)
            if not state.get('warned'):
                out.send(state['chat'],'Email checks paused by Google access/quota/account error. No actions taken. Reconnect or turn checks off/on after checking the account.')
                state['warned']=True;state['paused']=True;db.kv_set(KEY(OWNER),state)
