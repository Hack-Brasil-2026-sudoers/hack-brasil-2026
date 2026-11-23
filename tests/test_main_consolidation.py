"""Keep the local reports and cookies private while adopting main's auth/store contracts."""
import json
import sqlite3
import time

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from cybercheck.api import create_app
from cybercheck.auth import Auth, SESSION_COOKIE, digest
from cybercheck.config import Settings
from cybercheck.github import GitHubError
from cybercheck.store import Store


def legacy_store(directory, key):
    directory.mkdir(exist_ok=True)
    cipher=Fernet(key.encode())
    with sqlite3.connect(directory/'cybercheck.sqlite3') as db:
        db.execute('''CREATE TABLE analyses (
            id TEXT PRIMARY KEY, kind TEXT NOT NULL DEFAULT 'repository', repository_id INTEGER,
            repository TEXT, commit_sha TEXT, requested_ref TEXT, target_url TEXT,
            status TEXT NOT NULL DEFAULT 'queued', created_at TEXT NOT NULL, started_at TEXT,
            finished_at TEXT, dependency_lookup INTEGER NOT NULL, findings TEXT NOT NULL DEFAULT '[]',
            checks TEXT NOT NULL DEFAULT '[]', requests TEXT NOT NULL DEFAULT '[]',
            limitations TEXT NOT NULL DEFAULT '[]', error TEXT, owner_id INTEGER, installation_id INTEGER
        )''')
        for identity, owner in [('first',1),('second',2),('legacy',None)]:
            db.execute("INSERT INTO analyses(id,repository,commit_sha,created_at,dependency_lookup,owner_id,installation_id) "
                       "VALUES(?,?,?,?,?,?,?)",(identity,'team/project','a'*40,'2026-11-23T00:00:00Z',0,owner,500 if owner else None))
        db.execute('CREATE TABLE github_users (id INTEGER PRIMARY KEY,login TEXT,credentials BLOB,installation_id INTEGER,installation_account TEXT)')
        db.execute('CREATE TABLE sessions (id_hash TEXT PRIMARY KEY,user_id INTEGER,csrf TEXT,expires REAL)')
        token=cipher.encrypt(json.dumps({'access_token':'synthetic-user-token','expires':time.time()+3600,'refresh_token':'synthetic-refresh'}).encode())
        db.execute('INSERT INTO github_users VALUES(?,?,?,?,?)',(1,'alice',token,500,'team'))
        db.execute('INSERT INTO sessions VALUES(?,?,?,?)',(digest('existing-cookie'),1,'old-csrf',time.time()+86400))


def settings_for(directory,key):
    return Settings(api_token='x'*40,data_dir=directory,github_client_id='client',github_client_secret='secret',session_key=key)


def test_owner_migration_preserves_each_users_reports_and_legacy_operator_scope(tmp_path):
    key=Fernet.generate_key().decode();legacy_store(tmp_path,key)
    store=Store(tmp_path)
    assert store.get('first',owner='github:1')['id']=='first'
    assert store.get('first',owner='github:2') is None
    assert store.get('first') is None
    assert store.get('legacy')['id']=='legacy'
    assert [item['id'] for item in store.list(owner='github:2')]==['second']
    assert Store(tmp_path).get('first',owner='github:1')['owner']=='github:1'


def test_cookie_migration_uses_new_csrf_and_does_not_resurrect_logged_out_sessions(tmp_path):
    key=Fernet.generate_key().decode();legacy_store(tmp_path,key)
    store=Store(tmp_path);settings=settings_for(tmp_path,key)
    auth=Auth(settings,store)
    identity=auth.current('existing-cookie')
    assert identity['owner']=='github:1' and identity['token']=='synthetic-user-token'
    assert identity['csrf_token']!='old-csrf'
    assert auth.token_for_owner('github:1')=='synthetic-user-token'
    auth.logout('existing-cookie')
    assert Auth(settings,Store(tmp_path)).current('existing-cookie') is None
    with store.connect() as db:
        assert db.execute('SELECT count(*) FROM schema_migrations').fetchone()[0]==1
    assert b'synthetic-user-token' not in store.path.read_bytes()


def test_wrong_encryption_key_rolls_back_session_migration(tmp_path):
    key=Fernet.generate_key().decode();legacy_store(tmp_path,key)
    store=Store(tmp_path)
    with pytest.raises(GitHubError,match='migrate'):
        Auth(settings_for(tmp_path,Fernet.generate_key().decode()),store)
    assert Auth(settings_for(tmp_path,key),store).current('existing-cookie')['owner']=='github:1'


def test_existing_callback_and_reports_work_after_migration_without_trusting_installation_id(tmp_path):
    key=Fernet.generate_key().decode();legacy_store(tmp_path,key)
    settings=settings_for(tmp_path,key)
    with TestClient(create_app(settings)) as client:
        client.cookies.set(SESSION_COOKIE,'existing-cookie')
        assert client.get('/auth/me').json()['user']['id']==1
        assert client.get('/api/analyses/00000000-0000-0000-0000-000000000000').status_code==404
        assert [a['id'] for a in client.get('/api/analyses').json()['analyses']]==['first']
        response=client.get('/auth/github/setup?installation_id=999999&state=forged',follow_redirects=False)
        assert response.status_code==303 and response.headers['location']=='/app/#integrations'
        assert client.get('/auth/me').json()['user']['id']==1
        with client.app.state.store.connect() as db:
            assert db.execute('SELECT installation_id FROM github_users WHERE id=1').fetchone()[0]==500
        assert client.get('/api/auth/status').json()['github_enabled'] is True
        assert client.get('/',follow_redirects=False).headers['location']=='/app/'
        assert client.get('/app/').status_code==200


def test_previous_env_key_is_a_compatibility_alias_and_canonical_key_wins(tmp_path,monkeypatch):
    old=Fernet.generate_key().decode();new=Fernet.generate_key().decode()
    for name,value in {'GITHUB_CLIENT_ID':'client','GITHUB_CLIENT_SECRET':'secret','CYBERCHECK_AUTH_KEY':old,
                       'CYBERCHECK_SESSION_KEY':'','CYBERCHECK_DATA_DIR':str(tmp_path)}.items():monkeypatch.setenv(name,value)
    assert Settings.from_env().session_key==old
    monkeypatch.setenv('CYBERCHECK_SESSION_KEY',new)
    assert Settings.from_env().session_key==new
