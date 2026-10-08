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
