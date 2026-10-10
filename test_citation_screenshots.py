import cr_citations as C
import cr_screenshots as S
import cr_telegram as T

def test_wrong_page_programmes_rejected(monkeypatch):
 monkeypatch.setattr(C.llm,'ask_json',lambda *a,**k:{'claims':[{'claim':'It offers undergraduate programmes','url':'https://site.org/terms-and-conditions','quote':'This site offers undergraduate programmes'}]})
 assert 'do not support' in C.checked_answer('programmes','draft',[{'url':'https://site.org/terms-and-conditions','text':'This site offers undergraduate programmes'}])

def test_quote_must_belong_to_exact_page(monkeypatch):
 monkeypatch.setattr(C.llm,'ask_json',lambda *a,**k:{'claims':[{'claim':'A programme','url':'https://site.org/other','quote':'Actual programme offering description here'}]})
 assert 'do not support' in C.checked_answer('q','draft',[{'url':'https://site.org/course','text':'Actual programme offering description here'},{'url':'https://site.org/other','text':'Other page'}])

def test_supported_claim(monkeypatch):
 monkeypatch.setattr(C.llm,'ask_json',lambda *a,**k:{'claims':[{'claim':'Course offered','url':'https://site.org/course','quote':'Actual programme offering description here'}]})
 assert 'Source: https://site.org/course' in C.checked_answer('q','draft',[{'url':'https://site.org/course','text':'Actual programme offering description here'}])

def test_group_screenshot_no_private_optin(monkeypatch):
 calls=[]
 monkeypatch.setattr(S,'capture',lambda uid,text: calls.append(uid) or ('Webpage screenshot: https://example.com',{'filename':'screen.png','mime':'image/png','data':b'png'}))
 monkeypatch.setattr(T.mem,'user_lock',lambda *a: (_ for _ in ()).throw(AssertionError('No personal model')))
 monkeypatch.setattr(T.db,'kv_get',lambda *a:None)
 out=T.CaptureOut()
 T.handle_update({'message':{'chat':{'id':-991,'type':'supergroup'},'from':{'id':22},'text':'@crayon_v1_bot send screenshots of example.com','message_id':1}},out)
 assert calls==[22] and out.sent[0]['text']=='Attachment: screen.png'

def test_missing_link_and_plural():
 assert S.requested('Send screenshots please')
 assert S.capture(22,'send screenshots')[1] is None
 assert S.url_from('screenshot mastersunion.org')=='https://mastersunion.org'
