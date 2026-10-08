import pytest
import cr_computer as K
import os
os.environ.setdefault('CRAYON_BRIDGE_URL','https://example.com')
os.environ.setdefault('CRAYON_BRIDGE_TOKEN','test-only')
import computer_worker as W

def test_other_users_blocked():
    assert not K.status(12)['ok']
    assert not K.execute(12,'status',{})['ok']

def test_path_blocked():
    for x in ('../secret','.env','folder/x','/tmp/x'):
        with pytest.raises(ValueError):K.validate('read_text',{'filename':x})

def test_arithmetic_no_code():
    assert W.arithmetic('20 * (3+2) / 4')==25
    for x in ('__import__("os")','2 ** 1000000','open("x")','[1]*1000000'):
        with pytest.raises(ValueError):W.arithmetic(x)

def test_file_no_overwrite(tmp_path,monkeypatch):
    monkeypatch.setattr(W,'ROOT',tmp_path)
    assert W.run('write_text',{'filename':'proof.txt','text':'hello'})['verified']
    assert W.run('read_text',{'filename':'proof.txt'})['text']=='hello'
    with pytest.raises(FileExistsError):W.run('write_text',{'filename':'proof.txt','text':'bad'})

def test_browser_allowlist():
    from computer_browser import allowed
    for url in ('http://example.com','https://127.0.0.1','https://accounts.google.com','https://docs.github.com/login','https://docs.python.org:1234','https://example.com@evil.com'):
        with pytest.raises(ValueError):allowed(url)


def test_queue_retention(monkeypatch):
    queries=[]
    monkeypatch.setattr(K.db,'q',lambda sql,args,mode:queries.append(sql))
    monkeypatch.setattr(K.db,'kv_set',lambda *a:None)
    K.next_job({'system':'Linux'})
    assert queries[0].startswith('DELETE FROM computer_jobs')
    assert "30 minutes" in queries[0]
