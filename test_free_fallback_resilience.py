from contextvars import Context
import pytest
from langchain_core.messages import AIMessage
import cr_llm as L
import cr_config as C
import cr_lc as LC

@pytest.fixture(autouse=True)
def settings(monkeypatch):
    monkeypatch.setattr(C,'LLM_PROVIDER','gemini')
    monkeypatch.setattr(C,'OPENROUTER_AUTO_FALLBACK',True)
    monkeypatch.setattr(C,'OPENROUTER_KEY','synthetic')
    monkeypatch.setattr(L,'_free_catalog',lambda:{m:{'supported_parameters':['tools','response_format']} for m in L._FREE_MODELS})
    monkeypatch.setattr(L.time,'sleep',lambda *a:None)

def primary_failure(*a,**k):raise L.LLMError('quota','Synthetic')

def test_next_free_model_answers_after_429(monkeypatch):
    monkeypatch.setattr(L,'_generate_primary',primary_failure);seen=[]
    class Chat:
        def __init__(self,model):self.model=model
        def invoke(self,*a):
            if self.model==L._FREE_MODELS[0]:raise RuntimeError('429')
            return AIMessage(content='ready')
    monkeypatch.setattr(LC,'build_model',lambda model,*a,**kw:seen.append(model) or Chat(model))
    r=L.generate([L.user('synthetic')]);assert r['text']=='ready' and r['model']==L._FREE_MODELS[1]
    assert seen==list(L._FREE_MODELS[:2])

def test_exhausted_chain_honest_busy_not_success(monkeypatch):
    monkeypatch.setattr(L,'_generate_primary',primary_failure);seen=[]
    def blocked(model,*a,**k):seen.append(model);raise RuntimeError('429')
    monkeypatch.setattr(LC,'build_model',blocked)
    r=L.generate([L.user('synthetic')]);assert r['raw']['busy'] and r['raw']['completed'] is False
    assert r['calls']==[] and r['model']=='none' and "already confirmed above still count" in r['text']
    assert seen==[*L._FREE_MODELS,'openrouter/free']

@pytest.mark.parametrize('pricing',[{}, {'prompt':'0'}, {'prompt':'NaN','completion':0}, {'prompt':'0','completion':0,'request':'0.1'}, {'prompt':False,'completion':0}, {'prompt':'0','completion':0,'tier':[{'image':'0.01'}]}, {'prompt':'0','completion':0,'request':None}, {'prompt':'1e-99999','completion':'0'}])
def test_price_fail_closed(pricing):assert not L._zero_price(pricing)

def test_all_zero_nested_prices():assert L._zero_price({'prompt':'0','completion':'0.0','tier':[{'request':'0'}]})

def test_catalog_failure_no_stale_route(monkeypatch):
    monkeypatch.undo();monkeypatch.setattr(L,'_catalog',{'expires':0,'models':{'openrouter/free':{}}})
    monkeypatch.setattr(L.httpx,'get',lambda *a,**kw:(_ for _ in ()).throw(RuntimeError('offline')))
    assert L._free_catalog()=={}

def test_probe_does_not_change_parallel_context(monkeypatch):
    monkeypatch.setattr(L,'_generate_primary',lambda *a:{'text':'ordinary'})
    token=L._failover_probe.set({'attempts':[]})
    try:assert Context().run(L.generate,[L.user('synthetic')])['text']=='ordinary'
    finally:L._failover_probe.reset(token)

def test_auth_failure_stops_retries(monkeypatch):
    seen=[]
    def denied(model,*a,**kw):seen.append(model);raise RuntimeError('401')
    monkeypatch.setattr(LC,'build_model',denied)
    with pytest.raises(L.LLMError,match='auth'):L.openrouter_fallback([L.user('synthetic')])
    assert len(seen)==1

def test_tool_calls_preserved(monkeypatch):
    class Chat:
        def invoke(self,*a):return AIMessage(content='',tool_calls=[{'name':'lookup','args':{},'id':'x'}])
    monkeypatch.setattr(LC,'build_model',lambda *a,**kw:Chat())
    assert L.openrouter_fallback([L.user('synthetic')],tools=[{}])['calls'][0]['name']=='lookup'
