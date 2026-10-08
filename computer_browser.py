"""Fresh public-only Chromium. No credentials, forms, arbitrary selectors or JS tools."""
import base64,ipaddress,socket
from urllib.parse import urlsplit
# Public-only browsing. This denylist is a safety backstop, not a category classifier.
SENSITIVE={'mail.google.com','outlook.live.com','outlook.office.com','mail.yahoo.com','proton.me','protonmail.com','accounts.google.com','login.microsoftonline.com','paypal.com','stripe.com','chase.com','bankofamerica.com','hdfcbank.com','icicibank.com','onlinesbi.sbi','netbanking.hdfcbank.com','mychart.org'}
def allowed(url):
    p=urlsplit(url)
    host=(p.hostname or '').lower().rstrip('.')
    if p.scheme!='https' or not host or p.username or p.password or p.port not in (None,443):raise ValueError('Only public HTTPS websites, no credentials or custom ports')
    if any(host==h or host.endswith('.'+h) for h in SENSITIVE):raise ValueError('Sensitive account portal is blocked')
    import re
    if re.search(r'(?:^|[./_-])(?:banking|netbanking|webmail|patient|mychart|checkout|payment|wallet|logout|signout|settings)(?:[./_-]|$)',host+p.path.lower()):raise ValueError('Sensitive account or transaction portal is blocked')
    for x in socket.getaddrinfo(host,443):
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
        context.route_web_socket('**/*',lambda ws:ws.close())
        page=context.new_page();page.set_default_timeout(10000)
        def visit(url):
            allowed(url)
            response=page.goto(url,wait_until='domcontentloaded',timeout=30000)
            if not response or response.status>=500:raise ValueError('Page was not available')
            allowed(page.url)
            log.append('Visited '+page.url)
            if response.status>=400:log.append('Site returned HTTP '+str(response.status)+'; screenshot shows the visible wall/error page')
            body=page.locator('body').inner_text()[:4500]
            if any(x in body.lower() for x in ('log in to continue','sign in to continue','login to continue','log into instagram','log in','sign in','verify you are human')):log.append('Visible login or access wall. No sign-in attempted.')
            pages.append({'url':page.url,'title':page.title(),'text':body})
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
