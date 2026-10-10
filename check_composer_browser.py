"""Composer geometry and interactions; requests captured, never live actions."""
import json,time
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).parent/'docs'
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
 for w in [320,390,1280]:
  for dark in [False,True]:
   c=b.new_context(viewport={'width':w,'height':844});calls=[];errors=[]
   c.add_init_script("localStorage.setItem('crayon.web.session',JSON.stringify({token:'"+'a'*43+"',expires:Date.now()+3600000}));window.SpeechRecognition=class {start(){window.fakeRecognition=this;this.onstart()}stop(){this.onend()}};")
   def route(r):
    u=r.request.url
    if u.startswith('https://fixture.local/'):
     file=root/u.split('https://fixture.local/')[1].split('?')[0];file=file/'index.html' if file.is_dir() else file;r.fulfill(path=str(file));return
    if '/web/' not in u:r.abort();return
    path=u.split('/web/')[1];body=json.loads(r.request.post_data or '{}');calls.append((path,body));v={'messages':[],'conversations':[],'has_more':False}
    if path=='intent':v={'route':'chat','args':{},'ticket':'fixture-ticket'}
    if path=='me':v={'id':1,'name':'Composer fixture','expires_at':time.time()+3600}
    if path=='chat':v={'state':'queued'}
    if path.startswith('result?'):v={'state':'done','items':[{'kind':'text','text':'Fixture reply'}],'progress':[]}
    r.fulfill(content_type='application/json',body=json.dumps(v))
   c.route('**/*',route);page=c.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.goto('https://fixture.local/');page.wait_for_function('!document.querySelector("#input").disabled')
   if dark:page.click('#theme')
   initial=page.locator('#form').bounding_box();inp=page.locator('#input').bounding_box();assert inp['width']>initial['width']*.85,(w,inp,initial);assert initial['height']<125
   for id in ['attach','mic','send','research-focus']:
    rect=page.locator('#'+id).bounding_box();assert rect['height']>=44 and rect['x']>=initial['x'] and rect['x']+rect['width']<=initial['x']+initial['width']+1,(w,id,rect)
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   page.locator('#file').set_input_files({'name':'fixture.txt','mimeType':'text/plain','buffer':b'Private attachment fixture'})
   assert 'fixture.txt' in page.locator('#attachment-stage').inner_text();assert not any(x[0]=='upload' for x in calls)
   page.get_by_role('button',name='Remove',exact=True).click();assert page.locator('#attachment-stage').is_hidden()
   page.on('dialog',lambda d:d.accept());page.click('#mic');assert page.locator('#mic').get_attribute('aria-pressed')=='true';assert page.locator('#mic').get_attribute('aria-label')=='Stop recording';page.click('#mic');assert page.locator('#mic').get_attribute('aria-pressed')=='false';assert not any(x[0]=='chat' for x in calls)
   page.select_option('#research-focus','deep');page.fill('#input','A long sentence to resize the composer.\n'*12);assert page.locator('#input').bounding_box()['height']>=100
   page.press('#input','Shift+Enter');assert not any(x[0]=='chat' for x in calls)
   page.press('#input','Enter');page.wait_for_function('document.querySelector("#status").textContent==="Request done"');chats=[x for x in calls if x[0]=='chat'];assert len(chats)==1 and chats[0][1]['research_focus']=='deep' and chats[0][1]['intent_ticket']=='fixture-ticket';assert page.locator('#input').bounding_box()['height']<60
   assert page.locator('#send').is_disabled();page.screenshot(path=f'/downloads/composer-{w}-'+('dark' if dark else 'light')+'.png')
   # External select wrappers must not steal the text lane.
   page.evaluate('const s=document.querySelector("#research-focus");const wrap=document.createElement("div");s.before(wrap);wrap.append(s);wrap.style.width="180px"')
   assert page.locator('#input').bounding_box()['width']>initial['width']*.85
   assert not errors,errors;print(w,'dark' if dark else 'light','geometry/upload/mic/ShiftEnter/mode/send/reset/wrapper PASS');c.close()
 b.close()
