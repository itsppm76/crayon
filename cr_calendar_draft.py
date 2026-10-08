"""Private primary-calendar draft with exact review, atomic one-use create and readback."""
import re,json,time,secrets,hashlib
from datetime import datetime,timezone
import cr_google as G
import cr_db as db
URL='https://www.googleapis.com/calendar/v3/calendars/primary/events'
def init():
    db.q("CREATE TABLE IF NOT EXISTS google_calendar_drafts(id TEXT PRIMARY KEY,user_id BIGINT NOT NULL,encrypted_content TEXT NOT NULL,content_hash TEXT NOT NULL,status TEXT DEFAULT 'pending',expires_at TIMESTAMPTZ NOT NULL)",fetch='none')
def validate(content):
    if not isinstance(content,dict):raise G.GoogleError('Invalid calendar preview')
    if set(content)!={'account','summary','start','end','timezone'}:raise G.GoogleError('Unexpected calendar fields')
    if not isinstance(content['summary'],str) or not content['summary'].strip() or len(content['summary'])>100:raise G.GoogleError('Use a title of1-100 characters')
    from zoneinfo import ZoneInfo
    try:
        z=ZoneInfo(content['timezone']);a=datetime.fromisoformat(content['start']);b=datetime.fromisoformat(content['end'])
        if a.tzinfo is None or b.tzinfo is None or a.utcoffset()!=a.astimezone(z).utcoffset() or b.utcoffset()!=b.astimezone(z).utcoffset():raise ValueError()
        if b<=a or (b-a).total_seconds()>86400 or a<=datetime.now(timezone.utc):raise ValueError()
    except Exception:raise G.GoogleError('Use future ISO start/end with offsets matching the timezone; duration under24hours') from None
    return content
def preview(uid,title,start,end,tz):
    init();db.q("DELETE FROM google_calendar_drafts WHERE expires_at<now()",fetch='none');account=G.status(uid).get('email')
    if not account:raise G.GoogleError('Connect Google first')
    from cr_safety import clean_text,looks_like_secret
    if looks_like_secret(title):raise G.GoogleError('Title appears to contain a secret')
    c=validate({'account':account,'summary':clean_text(title),'start':start,'end':end,'timezone':tz})
    h=hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest();ident=secrets.token_hex(8)
    db.q("DELETE FROM google_calendar_drafts WHERE user_id=%s AND status='pending'",(uid,),'none')
    db.q("INSERT INTO google_calendar_drafts(id,user_id,encrypted_content,content_hash,expires_at) VALUES(%s,%s,%s,%s,now()+interval '10 minutes')",(ident,uid,G.encrypt(uid,c),h),'none')
    db.kv_set('calendar_reviewed_'+str(uid),[ident,h[:12]])
    return {'id':ident,'hash':h[:12],'text':'Calendar preview only, not booked. Expires in10minutes.\nAccount: '+account+'\nCalendar: primary\nTitle: '+c['summary']+'\nStart: '+start+'\nEnd: '+end+'\nTimezone: '+tz+'\nPrivate solo event. No attendees, invitations, notifications or video link. Existing events checked again before Create. Creating is not a venue/service booking.'}
def cancel(uid,ident):
    init();db.q("DELETE FROM google_calendar_drafts WHERE id=%s AND user_id=%s AND status='pending'",(ident,uid),'none');return 'Preview cancelled. No calendar event created.'
def create(uid,ident,h):
    init()
    if db.kv_get('calendar_reviewed_'+str(uid),None)!=[ident,h]:raise G.GoogleError('Review the current preview first')
    row=db.q("UPDATE google_calendar_drafts SET status='creating' WHERE id=%s AND user_id=%s AND status='pending' AND expires_at>now() AND left(content_hash,12)=%s RETURNING encrypted_content,content_hash",(ident,uid,h),'one')
    if not row:raise G.GoogleError('Preview expired, changed or already used')
    try:
        c=G.decrypt(uid,row['encrypted_content']);validate(c)
        if hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest()!=row['content_hash'] or G.status(uid).get('email')!=c['account']:raise G.GoogleError('Preview/account changed')
        events=G.request(uid,URL,{'timeMin':c['start'],'timeMax':c['end'],'singleEvents':'true','maxResults':100})
        if events.get('nextPageToken') or any(e.get('status')!='cancelled' and e.get('transparency')!='transparent' for e in events.get('items',[])):raise G.GoogleError('Slot conflicts or availability incomplete. Review a different slot.')
        token=G._access(uid)
        # Required scope is checked before write; existing read-only connections fail here.
        with G.httpx.Client(timeout=20) as client:
            info=client.get('https://oauth2.googleapis.com/tokeninfo',params={'access_token':token})
            if info.status_code!=200 or 'https://www.googleapis.com/auth/calendar.events' not in info.json().get('scope','').split():raise G.GoogleError('Reconnect Google with calendar write permission, then review a fresh preview')
            body={'id':'crayon'+ident,'summary':c['summary'],'start':{'dateTime':c['start'],'timeZone':c['timezone']},'end':{'dateTime':c['end'],'timeZone':c['timezone']},'visibility':'private'}
            r=client.post(URL,params={'sendUpdates':'none'},json=body,headers={'Authorization':'Bearer '+token})
            if r.status_code not in (200,201):raise G.GoogleError('Calendar create unconfirmed. Check Calendar before retrying.')
            data=r.json()
            stored=client.get(URL+'/'+body['id'],headers={'Authorization':'Bearer '+token})
            if stored.status_code!=200:raise G.GoogleError('Created response received but readback failed. Check Calendar, do not retry.')
            e=stored.json()
            if e.get('visibility')!='private' or e.get('conferenceData') or e.get('id')!=body['id'] or e.get('summary')!=c['summary'] or e.get('attendees') or any(datetime.fromisoformat(e[k]['dateTime'])!=datetime.fromisoformat(c[k]) for k in ('start','end')):raise G.GoogleError('Calendar readback mismatch. Check Calendar, do not retry.')
            link=e.get('htmlLink','')
        db.q('DELETE FROM google_calendar_drafts WHERE id=%s AND user_id=%s',(ident,uid),'none')
        return 'Created and read back on your primary calendar. No invitations. '+link
    except Exception as e:
        db.q("UPDATE google_calendar_drafts SET status='stopped' WHERE id=%s AND user_id=%s",(ident,uid),'none')
        raise G.GoogleError(str(e) if isinstance(e,G.GoogleError) else 'Calendar outcome uncertain. Check Calendar, do not retry.') from None
