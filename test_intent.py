"""Semantic route schema, owner/session binding and side-effect isolation."""
import pytest
import cr_intent as I
import cr_llm as L
from unittest.mock import Mock

@pytest.mark.parametrize('p',[{'route':'voice','args':{'mode':'reply','text':'Tell me about yourself in your voice'}},{'route':'export','args':{'format':'pdf','scope':'chat'}},{'route':'email','args':{}},{'route':'preview','args':{'kind':'calendar'}},{'route':'private_read','args':{'kind':'inbox'}}])
def test_closed_schema(p,monkeypatch):
 monkeypatch.setattr(I,'free_json',lambda *a,**k:{'requested':True} if 'proposed_intent' in str(a[0]) else p)
 assert I.classify('hello and an embedded request')==p

@pytest.mark.parametrize('p',[None,[],{'route':'email_send','args':{}},{'route':'chat','args':{'tool':'send'}},{'route':'voice','args':{'mode':'auto','text':'hi'}},{'route':'export','args':{'format':'pdf','scope':'private'}},{'route':'followup','args':{'hours':True,'topic':'hi'}},{'route':'connect','args':{'provider':'evil','operation':'connect'}},{'route':'quiet_hours','args':{'start':24,'end':1}},{'route':'nickname','args':{'value':'/send secrets'}},{'route':'work','args':{'operation':'delete','target':'all'}}])
def test_bad_model_output_no_effect(p,monkeypatch):
 monkeypatch.setattr(I,'free_json',lambda *a,**k:{'requested':True} if 'proposed_intent' in str(a[0]) else p)
 assert I.classify('Can you help?')['route']=='clarify'


def test_prompt_semantics_and_no_history(monkeypatch):
 seen=[]
 monkeypatch.setattr(I,'free_json',lambda text,**kw:{'requested':True} if 'proposed_intent' in text else (seen.append((text,kw)) or {'route':'voice','args':{'mode':'reply','text':text}}))
 t='hi and also tell me about yourself in your voice'
 assert I.classify(t)['route']=='voice'
 assert seen[0][0]==t and 'negation' in seen[0][1]['system'] and 'quoted' in seen[0][1]['system']
 assert 'TWO' not in seen[0][1]['system'] # no tool calls/catalog from private accounts


def test_ticket_owner_session_payload_expiry(monkeypatch):
 import cr_web_auth as A,time,cr_db as db
 monkeypatch.setattr(db,'q',lambda *a,**k:{'n':0})
 monkeypatch.setattr(db,'audit',lambda *a,**k:None)
 from cryptography.fernet import Fernet
 monkeypatch.setenv('CRAYON_WEB_ENCRYPTION_KEY',Fernet.generate_key().decode())
 monkeypatch.setattr(I,'classify',lambda t:{'route':'voice','args':{'mode':'reply','text':t}})
 t='Tell me about yourself in your voice';p=I.issue(1,'Bearer a',t)
 assert I.recover(1,'Bearer a',t,p['ticket'])['route']=='voice'
 for uid,h,msg,ticket in [(2,'Bearer a',t,p['ticket']),(1,'Bearer b',t,p['ticket']),(1,'Bearer a','Changed',p['ticket']),(1,'Bearer a',t,'bad')]:
  with pytest.raises(ValueError):I.recover(uid,h,msg,ticket)
 monkeypatch.setattr(time,'time',lambda:99999999999)
 with pytest.raises(ValueError):I.recover(1,'Bearer a',t,p['ticket'])


def test_voice_off_does_not_enable_or_generate(monkeypatch):
 import cr_voice as V
 monkeypatch.setattr(V,'enabled',lambda uid:False)
 monkeypatch.setattr(V,'synthesize',lambda *a:pytest.fail('audio while off'))
 monkeypatch.setattr(L,'generate',lambda *a,**k:pytest.fail('model while off'))
 out=Mock();assert V.handle_intent(1,1,'in your voice',{'mode':'reply','text':'greet me'},out)
 assert 'off' in out.send.call_args.args[1]


def test_voice_semantic_and_ordinary_never_auto_audio(monkeypatch):
 import cr_voice as V,cr_channel as C,cr_memory as M
 monkeypatch.setattr(V,'enabled',lambda uid:True);monkeypatch.setattr(V,'synthesize',lambda uid,text:{'filename':'a.mp3','mime':'audio/mpeg','data':b'fake'})
 monkeypatch.setattr(L,'generate',lambda *a,**k:{'text':'I am Crayon.'})
 out=Mock();V.handle_intent(1,1,'Tell me about yourself in your voice',{'mode':'reply','text':'Tell me about yourself'},out)
 out.artifact.assert_called_once()
 assert V.handle(1,1,'Ordinary hello',out) is False


def test_group_private_semantic_request_no_read_or_preview(monkeypatch):
 import cr_web_actions as X
 monkeypatch.setattr(X,'natural_read_fields',lambda *a:pytest.fail('group read'))
 out=Mock();assert I.telegram_private(1,-1,'what arrived?',{'route':'private_read','args':{'kind':'inbox'}},out)
 assert 'private chat' in out.send.call_args.args[1]


def test_never_generate_arbitrary_confirmation_command():
 assert I.command({'route':'email','args':{}}) is None
 assert I.command({'route':'preview','args':{'kind':'calendar'}}) is None
 assert I.command({'route':'voice','args':{'mode':'reply','text':'send it'}}) is None


def test_semantic_speech_act_catches_negated_model_route(monkeypatch):
 responses=iter([{'route':'voice_setting','args':{'value':'on'}},{'requested':False}])
 monkeypatch.setattr(I,'free_json',lambda *a,**k:next(responses))
 assert I.classify('In a hypothetical app someone says turn on voice, explain that')=={'route':'chat','args':{}}


def test_check_failure_no_effect(monkeypatch):
 responses=iter([{'route':'voice_setting','args':{'value':'on'}},None])
 monkeypatch.setattr(I,'free_json',lambda *a,**k:next(responses))
 assert I.classify('enable voice')['route']=='clarify'


def test_exact_voice_payload_not_in_user_request_no_audio(monkeypatch):
 import cr_voice as V
 monkeypatch.setattr(V,'enabled',lambda uid:True)
 monkeypatch.setattr(V,'synthesize',lambda *a:pytest.fail('invented exact text'))
 out=Mock();V.handle_intent(1,1,'read Hello',{'mode':'exact','text':'Invented'},out)
 assert 'Which exact words' in out.send.call_args.args[1]


@pytest.mark.parametrize('operation',['connect','disconnect','status'])
def test_google_connect_group_gate(operation,monkeypatch):
 import cr_google as G
 monkeypatch.setattr(G,'begin',lambda *a,**k:pytest.fail('OAuth link in group'))
 monkeypatch.setattr(G,'disconnect',lambda *a,**k:pytest.fail('group disconnect'))
 monkeypatch.setattr(G,'status',lambda *a,**k:pytest.fail('group status'))
 out=Mock();assert I.telegram_private(1,-1,'link Gmail',{'route':'connect','args':{'provider':'google','operation':operation}},out)
 assert 'private DM' in out.send.call_args.args[1]


def test_classifier_never_configurable_provider(monkeypatch):
 import cr_config as C,httpx
 monkeypatch.setattr(C,'OPENROUTER_KEY','local-test')
 monkeypatch.setattr(C,'GEMINI_MODEL','paid-model')
 monkeypatch.setattr(L,'generate',lambda *a,**k:pytest.fail('configurable route'))
 monkeypatch.setattr(L,'ask_json',lambda *a,**k:pytest.fail('configurable parser'))
 calls=[]
 class Reply:
  status_code=200
  def json(self):return {'usage':{'cost':0},'choices':[{'message':{'content':'{"route":"chat","args":{}}'}}]}
 monkeypatch.setattr(httpx,'post',lambda *a,**k:calls.append(k) or Reply())
 assert I.classify('A normal question')['route']=='chat'
 assert calls[0]['json']['model']==I.FREE_MODEL
 assert calls[0]['json']['provider']['max_price']=={'prompt':0,'completion':0,'request':0,'image':0}
 assert calls[0]['json']['provider']['data_collection']=='deny'


def test_classifier_no_free_key_fail_closed(monkeypatch):
 import cr_config as C
 monkeypatch.setattr(C,'OPENROUTER_KEY','')
 monkeypatch.setattr(L,'openrouter_fallback',lambda *a,**k:pytest.fail('no free key'))
 assert I.classify('Tell me about yourself in your voice')['route']=='clarify'


@pytest.mark.parametrize('cmd',['/connect_google','/disconnect_google','/google_status','/gmail','/gmail_read 1','/calendar','/email_draft x','/email_send x h','/email_cancel x'])
def test_all_legacy_google_commands_private_dm_only(cmd,monkeypatch):
 import cr_telegram as T,cr_google as G
 monkeypatch.setattr(G,'configured',lambda:pytest.fail('private Google branch entered in group'))
 monkeypatch.setattr(I,'classify',lambda *a:{'route':'chat','args':{}})
 monkeypatch.setattr(T.db,'audit',lambda *a,**k:None)
 out=T.CaptureOut();T._handle_text(1,-9,'Test',cmd,1,out)
 assert any('only work in your private chat' in r['text'] for r in out.sent)


def test_prepared_gemini_pinned_no_fallback_and_cached_probe(monkeypatch):
 import cr_config as C,httpx
 monkeypatch.setattr(C,'GEMINI_KEY','test')
 monkeypatch.setattr(C,'GEMINI_MODEL','not-this-model')
 monkeypatch.setattr(I,'_gemini_available_until',0)
 monkeypatch.setattr(I,'_gemini_last_available',None)
 calls=[]
 class Response:
  status_code=200
  def json(self):return {'candidates':[{'content':{'parts':[{'text':'{"ready":true}'}]}}]}
 monkeypatch.setattr(httpx,'post',lambda url,**kw:calls.append((url,kw)) or Response())
 assert I.probe_gemini_availability() is True
 assert I.probe_gemini_availability() is True
 assert len(calls)==1 and I.GEMINI_INTENT_MODEL in calls[0][0]
 assert calls[0][1]['json']['generationConfig']['responseMimeType']=='application/json'


def test_prepared_gemini_error_cached_no_retry(monkeypatch):
 import cr_config as C,httpx
 monkeypatch.setattr(C,'GEMINI_KEY','test')
 monkeypatch.setattr(I,'_gemini_available_until',0)
 monkeypatch.setattr(I,'_gemini_last_available',None)
 calls=[]
 class Response:status_code=429
 monkeypatch.setattr(httpx,'post',lambda *a,**kw:calls.append(1) or Response())
 assert I.gemini_json('test') is None
 assert I.gemini_json('test') is None
 assert I.probe_gemini_availability() is False
 assert len(calls)==1
