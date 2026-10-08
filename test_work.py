import cr_work as W
import pytest

def test_arithmetic_no_code():
    assert W.calculate('20*(3+2)/4')==25
    for bad in ('__import__("os")','2**100','sum([1,2])','1/0','[1]'):
        with pytest.raises(Exception):W.calculate(bad)

def test_plan_scope():
    title,steps=W.parse('Demo | calculate 2+2 | calculate 4*5')
    assert title=='Demo' and len(steps)==2
    for bad in ('send hello','email a@b.com','Demo | calculate 1 | calculate 2 | calculate 3 | calculate 4'):
        with pytest.raises(ValueError):W.parse(bad)

def test_evidence_page(monkeypatch):
    import cr_web
    monkeypatch.setattr(cr_web,'fetch',lambda *a:{'url':'https://example.com','title':'Example','text':'verified page'})
    r=W.step_run({'op':'page','input':'https://example.com'})
    assert r['sources']==['https://example.com'] and 'verified page' in r['text']

def test_no_sources_no_done(monkeypatch):
    import cr_web
    monkeypatch.setattr(cr_web,'research',lambda *a:{'pages':[]})
    with pytest.raises(ValueError):W.step_run({'op':'research','input':'demo'})

def test_job_view_honest():
    text=W.view({'id':2,'title':'Demo','status':'blocked','steps':[{'op':'calculate','input':'2+2'}],'results':[]})
    assert 'not completed' in text and '0/1' in text and 'Stopped' in text

def test_cross_user_control(monkeypatch):
    monkeypatch.setattr(W,'get',lambda *a:None)
    with pytest.raises(ValueError):W.control(10,2,'resume')

def test_not_auto_activate():
    class Out:
        def send(self,*a,**k):pytest.fail('no command')
    assert not W.handle(1,1,'do more automatically',Out())

def test_scheduled_writes_blocked():
    import cr_tools as T
    for tool,args in [('remember',{'key':'x','value':'y'}),('create_csv',{'headers':['x'],'rows':[['1']]}),('computer_browse',{'url':'https://example.com'})]:
        r=T.run(tool,args,{'uid':1,'readonly':True,'meta':{}})
        assert not r['ok'] and 'read-only' in r['error']
    names=[x['name'] for x in T.declarations(readonly=True)[0]['functionDeclarations']]
    assert 'research_web' in names and 'remember' not in names and 'computer_browse' not in names

def test_dashboard_no_invented_done(monkeypatch):
    import cr_dashboard as D
    monkeypatch.setattr(D.T,'list_tasks',lambda ctx:{'tasks':[{'id':4,'title':'Demo','done':0,'total':2,'steps':[{'n':1,'title':'Review','status':'blocked'},{'n':2,'title':'Write','status':'todo'}]}]})
    monkeypatch.setattr(D.T,'list_reminders',lambda ctx:{'reminders':[]})
    monkeypatch.setattr(W,'init',lambda:None)
    monkeypatch.setattr(D.db,'q',lambda *a:[])
    text=D.render(1)
    assert 'Blocked: Review' in text and 'Next 2: Write' in text and '0/2' in text

def test_brief_rejects_invented_link(monkeypatch):
    import cr_web,cr_llm
    monkeypatch.setattr(cr_web,'research',lambda *a:{'pages':[{'url':'https://example.com','text':'Evidence'}]})
    monkeypatch.setattr(cr_llm,'ask_json',lambda *a,**k:{'points':[{'claim':'fake','url':'https://evil.invalid'}]})
    with pytest.raises(ValueError):W.step_run({'op':'brief','input':'topic'})

def test_brief_source_bound(monkeypatch):
    import cr_web,cr_llm
    monkeypatch.setattr(cr_web,'research',lambda *a:{'pages':[{'url':'https://example.com','text':'Evidence'}]})
    monkeypatch.setattr(cr_llm,'ask_json',lambda *a,**k:{'answer':'Draft','points':[{'claim':'point','url':'https://example.com'}],'outline':['Intro'],'gaps':['Check']})
    r=W.step_run({'op':'brief','input':'topic'})
    assert r['draft'] and 'check before using' in r['text'] and 'https://example.com' in r['text']

def test_pause_running_cannot_resume(monkeypatch):
    row={'id':1,'user_id':1,'status':'running'};written=[]
    monkeypatch.setattr(W,'get',lambda *a:row)
    def q(sql,args,fetch):written.append(args);row['status']=args[0]
    monkeypatch.setattr(W.db,'q',q)
    W.control(1,1,'pause')
    assert row['status']=='pausing'
    with pytest.raises(ValueError):W.control(1,1,'resume')
