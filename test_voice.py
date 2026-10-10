import pytest
import cr_voice as V

def test_voice_off_no_network(monkeypatch):
    monkeypatch.setattr(V,'enabled',lambda uid:False)
    with pytest.raises(ValueError,match='off'):V.synthesize(1,'hello')

def test_voice_secret_no_network(monkeypatch):
    monkeypatch.setattr(V,'enabled',lambda uid:True)
    monkeypatch.setenv('ELEVENLABS_API_KEY','private');monkeypatch.setenv('ELEVENLABS_VOICE_ID','a'*20)
    with pytest.raises(ValueError):V.synthesize(1,'x'*1201)

def test_paid_plan_hard_stop(monkeypatch):
    monkeypatch.setattr(V,'enabled',lambda uid:True)
    monkeypatch.setenv('ELEVENLABS_API_KEY','private');monkeypatch.setenv('ELEVENLABS_VOICE_ID','a'*20)
    class R:
        def raise_for_status(self):pass
        def json(self):return {'tier':'starter'}
    class Client:
        def __init__(self,**kw):pass
        def __enter__(self):return self
        def __exit__(self,*a):pass
        def get(self,*a,**kw):return R()
        def post(self,*a,**kw):raise AssertionError('paid generation')
    monkeypatch.setattr(V.httpx,'Client',Client)
    with pytest.raises(ValueError,match='Free-only'):V.synthesize(1,'hello')

def test_auto_reply_fresh_scope_and_private_exclusion(monkeypatch):
    sent=[]
    class Out:
        def send(self,*args):sent.append(args)
        def artifact(self,*args):sent.append(args)
    state={'voice_optin_1':True}
    monkeypatch.setattr(V.db,'kv_get',lambda k,d=None:state.get(k,d))
    monkeypatch.setattr(V,'synthesize',lambda uid,text:{'filename':'reply.mp3','mime':'audio/mpeg','data':b'ok'})
    assert not V.reply_audio(1,1,'Hi',{},Out())
    state['voice_reply_optin_1']=True
    assert not V.reply_audio(1,-1,'Hi',{},Out())
    assert not V.reply_audio(1,1,'Inbox',{'tools':['read_email']},Out())
    assert not V.reply_audio(1,1,'x'*1201,{},Out())
    assert not sent
    assert V.reply_audio(1,1,'Hi',{},Out())
    assert len(sent)==2
