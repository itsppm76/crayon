import json,time
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).parent/'docs';effects=[]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
 for width in [390,1280]:
  c=b.new_context(viewport={'width':width,'height':844});c.add_init_script("if(location.hostname==='ux.local')localStorage.setItem('crayon.web.session',JSON.stringify({token:'"+'a'*43+"',expires:Date.now()+3600000}));")
  ticket=[0];state={'unknown':False,'expiry':False};html='<p>Exact fixture body<br>Line two with $50</p>'
  def route(r):
   u=r.request.url
   if u.startswith('https://ux.local/'):
    path=root/u.split('https://ux.local/')[1].split('?')[0];path=path/'index.html' if path.is_dir() else path;r.fulfill(path=str(path));return
   if '/web/' not in u:r.abort();return
   path=u.split('/web/')[1];body=json.loads(r.request.post_data or '{}')
   v={'id':1898030949,'name':'Fixture acceptance','expires_at':time.time()+3600} if path=='me' else {'messages':[],'has_more':False,'conversations':[]}
   if path=='intent':v={'route':'chat','args':{},'ticket':'fixture-ticket'}
   if path=='connections':v={'google':'owner@example.com','workspace':'owner@example.com'}
   if path=='action-preview':
    ticket[0]+=1;v={'review_id':'r'+str(ticket[0]),'hash':'h'+str(ticket[0]),'kind':body['kind'],'text':'From: owner@example.com\nTo: recipient@example.com\nSubject: UX fixture\n\nExact body $50 <script>alert(1)</script>\n'+('long line '*30),'html':html,'review_fields':body['fields'],'expires_in':0.1 if state['expiry'] else 600}
   if path.startswith('result?'):v={'state':'done','items':[{'kind':'text','text':'Hello after expiry'}],'progress':[]}
   if path=='action-confirm':
    effects.append(body);v={'state':'unknown' if state['unknown'] else 'cancelled' if body['decision']=='cancel' else 'done','text':'Outcome unconfirmed. Check destination.' if state['unknown'] else 'Cancelled. Nothing sent.' if body['decision']=='cancel' else 'Sent fixture receipt.'}
   r.fulfill(status=200,content_type='application/json',body=json.dumps(v))
  c.route('**/*',route);page=c.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto('https://ux.local/');page.wait_for_function("!document.querySelector('#input').disabled")
  page.click('#menu');page.click('#connections');page.get_by_role('button',name='Prepare email',exact=True).click()
  for label,value in [('TO (comma-separated exact emails)','recipient@example.com'),('SUBJECT','UX fixture'),('BODY','Exact body $50')]:page.get_by_label(label,exact=True).fill(value)
  page.get_by_role('button',name='Prepare exact preview',exact=True).click();page.wait_for_selector('.approval-card')
  assert not effects;assert page.locator('.approval-card .review').inner_text().find('<script>')!=-1
  assert page.locator('.approval-card iframe').get_attribute('sandbox')==''
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  page.evaluate("document.querySelector('#scroll').scrollTop=0");page.screenshot(path=f'/downloads/ux-approval-{width}.png')
  page.get_by_role('button',name='Edit and prepare a new review',exact=True).click();page.get_by_label('Exact fields (JSON)',exact=True).fill(json.dumps({'to':['new@example.com'],'cc':[],'bcc':[],'subject':'Changed','body':'Edited body'}));page.get_by_role('button',name='Prepare new preview',exact=True).click();page.wait_for_function("document.querySelector('.approval-card .review').textContent.includes('From:')")
  assert ticket[0]==2 and not effects
  page.get_by_role('button',name='Cancel',exact=True).click();page.wait_for_function("document.querySelector('.approval-card').dataset.outcome==='cancelled'");assert effects[-1]['review_id']=='r2' and effects[-1]['decision']=='cancel'
  page.screenshot(path=f'/downloads/ux-cancel-{width}.png')
  # Expired ticket cannot act, but normal chat must remain usable.
  state['expiry']=True
  page.click('#menu');page.click('#connections');page.get_by_role('button',name='Prepare email',exact=True).click()
  page.get_by_label('TO (comma-separated exact emails)',exact=True).fill('recipient@example.com')
  page.get_by_label('SUBJECT',exact=True).fill('Expiry');page.get_by_label('BODY',exact=True).fill('Secret')
  page.get_by_role('button',name='Prepare exact preview',exact=True).click()
  page.wait_for_function("[...document.querySelectorAll('.approval-card')].at(-1).dataset.outcome==='expired'")
  assert page.get_by_role('button',name='Send exactly this',exact=True).last.is_disabled()
  assert len(effects)==1
  page.fill('#input','Hello after expiry');page.click('#send')
  page.wait_for_function("[...document.querySelectorAll('.msg.user')].some(n=>n.textContent.includes('Hello after expiry'))")
  assert 'Use Cancel or Edit' not in page.locator('#status').inner_text()
  # Actual helper pixel fixture tests sequence, repeated labels, unknown state.
  page.evaluate("document.querySelector('#log').replaceChildren(CrayonUX.progress([{id:'a',seq:1,label:'Reading source',state:'running'},{id:'a',seq:2,label:'Reading source',state:'done'},{id:'b',seq:3,label:'Reading source',state:'running'},{id:'b',seq:4,label:'Reading source',state:'blocked'}],'unknown'))")
  assert page.locator('.work-steps li').count()==2;assert page.locator('.work-heading').inner_text()=='Outcome unconfirmed';page.screenshot(path=f'/downloads/ux-status-{width}.png')
  assert not errors;print(width,'preview/edit/cancel/HTML/sequence/unknown PASS',errors);c.close();effects.clear()
 b.close()
