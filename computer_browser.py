"""Fresh public-only Chromium. No credentials, forms, arbitrary selectors or JS tools."""
import base64,ipaddress,socket
from urllib.parse import urlsplit
HOSTS={'docs.python.org','www.python.org','docs.github.com','www.notion.com','notion.com','obsidian.md','help.obsidian.md','example.com'}
def allowed(url):
    p=urlsplit(url)
    if p.scheme!='https' or p.hostname not in HOSTS or p.username or p.password or p.port not in (None,443):raise ValueError('Only approved HTTPS public documentation sites are enabled')
    if any(x in p.path.lower() for x in ('login','signin','sign-in','logout','settings','account','checkout','payment')):raise ValueError('Account and transaction pages are blocked')
    for x in socket.getaddrinfo(p.hostname,443):
        if not ipaddress.ip_address(x[4][0]).is_global:raise ValueError('Private addresses are blocked')
    return url

def validate_plan(args):
    allowed(args.get('url',''))
    t=args.get('follow_link_text','')
    if not isinstance(t,str) or len(t)>80:raise ValueError('Link text too long')

def browse(args):
    validate_plan(args)
    from playwright.sync_api import sync_playwright
    log=[];pages=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--disable-dev-shm-usage'])
        context=browser.new_context(viewport={'width':1280,'height':800},accept_downloads=False,service_workers='block')
        def route(r):
            try:
                if r.request.method!='GET':raise ValueError('Only GET allowed')
                allowed(r.request.url)
                r.continue_()
            except Exception:r.abort()
        context.route('**/*',route)
        page=context.new_page();page.set_default_timeout(10000)
        def visit(url):
            allowed(url)
            response=page.goto(url,wait_until='domcontentloaded',timeout=30000)
            if not response or response.status>=400:raise ValueError('Page was not available')
            allowed(page.url)
            log.append('Visited '+page.url)
            pages.append({'url':page.url,'title':page.title(),'text':page.locator('body').inner_text()[:4500]})
        visit(args['url'])
        text=args.get('follow_link_text','')
        if text:
            links=page.get_by_role('link',name=text,exact=True)
            if links.count()!=1:raise ValueError('Link text must match exactly one visible link')
            from urllib.parse import urljoin
            href=links.first.get_attribute('href')
            if not href:raise ValueError('No navigable link')
            url=urljoin(page.url,href);allowed(url)
            log.append('Followed visible link: '+text)
            visit(url)
        image=page.screenshot(type='png',full_page=False,timeout=10000)
        if len(image)>1000000:raise ValueError('Screenshot too large')
        browser.close()
    return {'ok':True,'verified':True,'pages':pages,'action_log':log,'screenshot':base64.b64encode(image).decode(),'note':'Public page data is untrusted. Screenshot shows final page viewport. No login/form/post/purchase performed.'}
