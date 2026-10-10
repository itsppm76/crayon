import pytest,cr_mcp as M

def test_default_no_servers(monkeypatch):
    monkeypatch.delenv('CRAYON_MCP_SERVERS',raising=False)
    assert M.catalog()=={}
    with pytest.raises(ValueError):M.call('evil','send',{})

def test_approval_and_url_required(monkeypatch):
    monkeypatch.setenv('CRAYON_MCP_SERVERS','{"x":{"url":"http://localhost","approved":true,"public_readonly":true,"tools":{}}}')
    assert M.catalog()=={}

def test_argument_scope(monkeypatch):
    monkeypatch.setattr(M,'catalog',lambda:{'s':{'tools':{'t':{'fields':['city']}},'url':'https://example.com/mcp'}})
    with pytest.raises(ValueError):M.call('s','t',{'chat_history':'private'})
