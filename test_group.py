import cr_group as G
import cr_telegram as T


def test_mention_exact():
    assert G.mentioned({'text':'hi @crayon_v1_bot explain gravity'})
    assert not G.mentioned({'text':'hi @crayon_v1_bot_fake'})
    assert not G.mentioned({'text':'hello'})


def test_untagged_group_ignored(monkeypatch):
    monkeypatch.setattr(T.db,'kv_set',lambda *a: (_ for _ in ()).throw(AssertionError('private state touched')))
    out=T.CaptureOut()
    T.handle_update({'message':{'chat':{'id':-991,'type':'group'},'from':{'id':22},'text':'hello'}},out)
    assert not out.sent


def test_tagged_group_no_private_state(monkeypatch):
    monkeypatch.setattr(T.db,'kv_set',lambda *a: (_ for _ in ()).throw(AssertionError('private state touched')))
    monkeypatch.setattr(G,'answer',lambda msg:'Group answer')
    out=T.CaptureOut()
    T.handle_update({'message':{'chat':{'id':-991,'type':'supergroup'},'from':{'id':22},'text':'@crayon_v1_bot hi'}},out)
    assert out.sent[0]['text']=='Group answer'


def test_group_tools_disabled(monkeypatch):
    def gen(contents,system,tools):
        assert tools is None
        assert 'no private memory' in system
        return {'text':'Hi'}
    monkeypatch.setattr(G.llm,'generate',gen)
    assert G.answer({'text':'@crayon_v1_bot explain gravity'})=='Hi'

def test_group_news_explicit_public_lookup(monkeypatch):
    import cr_web as W
    calls=[]
    monkeypatch.setattr(W,'news',lambda q,n,day:calls.append((q,day)) or {'items':[{'title':'Test news','url':'https://news.google.com/test','source':'Publisher','published':'2026-10-09T10:00:00+05:30'}],'day':None})
    monkeypatch.setattr(G.llm,'generate',lambda *a,**kw:(_ for _ in ()).throw(AssertionError('no unsupported model news')))
    r=G.answer({'text':'@crayon_v1_bot tell me the latest AI news now','from':{'id':7555366869}})
    assert calls and 'Test news' in r and 'https://' not in r and 'Publisher' in r

def test_group_yesterday_resolves_date(monkeypatch):
    import cr_web as W
    from datetime import datetime,timedelta
    from zoneinfo import ZoneInfo
    calls=[]
    monkeypatch.setattr(W,'news',lambda q,n,day:calls.append(day) or {'items':[]})
    G.answer({'text':'@crayon_v1_bot yesterday news of india','from':{'id':1898030949}})
    assert calls==[datetime.now(ZoneInfo('Asia/Calcutta')).date()-timedelta(days=1)]

def test_group_private_and_unknown_lookup_blocked(monkeypatch):
    import cr_web as W
    monkeypatch.setattr(W,'news',lambda *a:(_ for _ in ()).throw(AssertionError('blocked')))
    assert 'never read' in G.answer({'text':'@crayon_v1_bot search my inbox','from':{'id':1898030949}})

def test_group_lookup_failure_no_fluff(monkeypatch):
    import cr_web as W
    monkeypatch.setattr(W,'news',lambda *a:(_ for _ in ()).throw(RuntimeError('HTTP503')))
    r=G.answer({'text':'@crayon_v1_bot latest news','from':{'id':1898030949}})
    assert 'failed' in r and 'happy' not in r and 'cutoff' not in r

def test_news_date_filter(monkeypatch):
    import cr_web as W
    from datetime import date
    import httpx
    xml=b'<rss><channel><item><title>old</title><pubDate>Wed, 07 Oct 2026 10:00:00 GMT</pubDate><link>https://news.google.com/old</link></item><item><title>fresh</title><source>Publisher</source><pubDate>Thu, 08 Oct 2026 10:00:00 GMT</pubDate><link>https://news.google.com/fresh</link></item><item><title>unsafe</title><pubDate>Thu, 08 Oct 2026 11:00:00 GMT</pubDate><link>http://localhost/private</link></item></channel></rss>'
    monkeypatch.setattr(W._c,'get',lambda *a,**kw:httpx.Response(200,content=xml))
    r=W.news('fresh',3,date(2026,10,8));assert [i['title'] for i in r['items']]==['fresh']


def test_public_news_any_tagged_user(monkeypatch):
    import cr_web as W
    monkeypatch.setattr(W,'news',lambda *a:{'items':[]})
    assert 'No dated news results' in G.answer({'text':'@crayon_v1_bot latest news','from':{'id':12}})


def test_group_news_clean_no_links(monkeypatch):
    import cr_web as W
    monkeypatch.setattr(W,'news',lambda *a:{'items':[{'title':'Clear headline','url':'https://news.google.com/test','source':'Publisher','published':'2026-10-09T10:00:00+05:30'}],'day':None})
    r=G.answer({'text':'@crayon_v1_bot latest news','from':{'id':12}})
    assert '1. Clear headline' in r and 'Publisher |' in r and 'https://' not in r and not hasattr(r,'markup')


def test_group_explicit_date_count_topic(monkeypatch):
    import cr_web as W
    from datetime import date
    calls=[];monkeypatch.setattr(W,'news',lambda q,n,d:calls.append((q,n,d)) or {'items':[]})
    G.answer({'text':'@crayon_v1_bot give top 5 news for Portugal from 8th Oct 2026','from':{'id':12}})
    assert calls==[('Portugal',5,date(2026,10,8))]


def test_group_portugal_clean_topic(monkeypatch):
    import cr_web as W
    calls=[];monkeypatch.setattr(W,'news',lambda q,n,d:calls.append(q) or {'items':[]})
    G.answer({'text':'@crayon_v1_bot okay give top 5 news for Portugal','from':{'id':12}})
    G.answer({'text':'@crayon_v1_bot can you give top 5 news from Portugal and Venezuela','from':{'id':12}})
    assert calls==['Portugal','Portugal','Venezuela']

def test_news_relevance_publisher_dedupe(monkeypatch):
    import cr_web as W,httpx
    from datetime import date
    xml=b'<rss><channel><item><title>Audio briefing - Publisher</title><source>Publisher</source><pubDate>Thu, 08 Oct 2026 10:00:00 GMT</pubDate><link>https://news.google.com/a</link></item><item><title>Portugal policy - Publisher</title><source>Publisher</source><pubDate>Thu, 08 Oct 2026 10:00:00 GMT</pubDate><link>https://news.google.com/b</link></item></channel></rss>'
    monkeypatch.setattr(W._c,'get',lambda *a,**kw:httpx.Response(200,content=xml))
    r=W.news('Portugal',5,date(2026,10,8));assert [i['title'] for i in r['items']]==['Portugal policy']
