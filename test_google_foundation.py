import pytest
from cryptography.fernet import Fernet
import cr_google as G


def test_encrypted_token_bound_to_user(monkeypatch):
    key=Fernet.generate_key().decode()
    monkeypatch.setenv('GOOGLE_TOKEN_ENCRYPTION_KEY',key)
    token={'refresh_token':'synthetic-secret'}
    blob=G.encrypt(11,token)
    assert 'synthetic-secret' not in blob
    assert G.decrypt(11,blob)==token
    with pytest.raises(G.GoogleError):
        G.decrypt(12,blob)
    with pytest.raises(G.GoogleError):
        G.decrypt(11,blob[:-3]+'bad')


def test_oauth_off_without_secrets(monkeypatch):
    monkeypatch.delenv('GOOGLE_CLIENT_ID',raising=False)
    assert not G.configured()
    with pytest.raises(G.GoogleError):
        G.begin(11)


def test_no_write_endpoint():
    with pytest.raises(G.GoogleError):
        G.request(11,'https://gmail.googleapis.com/gmail/v1/users/me/messages/send')


def test_oauth_state_replay_fails_before_token_exchange(monkeypatch):
    monkeypatch.setattr(G,'configured',lambda:True)
    monkeypatch.setattr(G.db,'q',lambda *a,**k:None)
    with pytest.raises(G.GoogleError,match='expired or already used'):
        G.complete('used-state','fake-code')


def test_no_other_users_token_read(monkeypatch):
    seen=[]
    def q(sql,params=(),fetch='all'):
        seen.append(params)
        return None
    monkeypatch.setattr(G,'configured',lambda:True)
    monkeypatch.setattr(G.db,'q',q)
    with pytest.raises(G.GoogleError,match='Connect your own'):
        G._access(22)
    assert seen==[(22,)]
