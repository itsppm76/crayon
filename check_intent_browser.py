"""Browser semantic route selection, captured transports, no external effects."""
import json,time
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).parent/'docs'
cases=[('Tell me about yourself in your voice','voice',{'mode':'reply','text':'Tell me about yourself'},'chat'),('Could I have this conversation in Markdown?','export',{'scope':'chat','format':'md'},'download'),('There is a lot in my inbox, what came today?','private_read',{'kind':'inbox'},'private-read'),('I need an email asking sam@example.com to buy a domain','email',{},'compose-preview'),('An hour of study tomorrow10am on my calendar please','preview',{'kind':'calendar'},'action-preview'),('I need a spreadsheet for weekly study','preview',{'kind':'workspace_create'},'action-preview'),('No voice note, just text please','chat',{},'chat')]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
 for width in [390,1280]:
  c=b.new_context(viewport={'width':width,'height':844},accept_downloads=True);calls=[];choice=[None]
  c.add_init_script("localStorage.setItem('crayon.web.session',JSON.stringify({token:'"+'a'*43+"',expires:Date.now()+3600000}));")
  def route(r):
   u=r.request.url
   if u.startswith('https://intent.local/'):
    path=root/u.split('https://intent.local/')[1].split('?')[0];path=path/'index.html' if path.is_dir() else path;r.fulfill(path=str(path));return
   if '/web/' not in u:r.abort();return
   path=u.split('/web/')[1];body=json.loads(r.request.post_data or '{}');calls.append((path,body));v={'messages':[],'conversations':[],'has_more':False}
   if path=='me':v={'id':1,'name':'Semantic fixture','expires_at':time.time()+3600}
   if path=='intent':v={'route':choice[0][1],'args':choice[0][2],'ticket':'fixture-ticket'}
   if path=='connections':v={'google':'owner@example.com'}
   if path in ('action-preview','compose-preview'):v={'kind':'clarification','text':'Missing exact detail','action':'calendar' if path=='action-preview' else None}
   if path=='private-read':v={'text':'PRIVATE_INBOX_ONLY_123','private':True}
   if path=='chat':v={'state':'queued'}
   if path.startswith('result?'):v={'state':'done','items':[{'kind':'text','text':'Fixture answer'}],'progress':[]}
   r.fulfill(content_type='application/json',body=json.dumps(v))
  c.route('**/*',route);page=c.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  for case in cases:
   choice[0]=case;calls.clear();page.goto('https://intent.local/');page.wait_for_function('!document.querySelector("#input").disabled')
   page.fill('#input',case[0]);page.click('#send')
   if case[3]=='download':
    page.wait_for_function('document.querySelector("a[download]")')
    assert not any(path in ('chat','private-read','action-preview','compose-preview') for path,body in calls)
   else:
    page.wait_for_function('!document.querySelector("#input").disabled')
    page.wait_for_timeout(250)
    assert sum(path==case[3] for path,body in calls)==1,(case,calls)
    assert not any(path=='action-confirm' for path,body in calls)
    if case[3]=='chat':
     page.wait_for_function('document.querySelector("#status").textContent==="Request done"')
     posted=next(body for path,body in calls if path=='chat');assert posted['message']==case[0] and posted['intent_ticket']=='fixture-ticket'
    if case[3]=='private-read':assert page.locator('dialog').inner_text().find('PRIVATE_INBOX_ONLY_123')>=0 and 'PRIVATE_INBOX_ONLY_123' not in page.locator('#log').inner_text()
   assert not errors;assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   print(width,case[1],case[3],'PASS')
  page.screenshot(path=f'/downloads/intent-browser-{width}.png');c.close()
 b.close()
