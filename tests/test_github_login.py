import base64
import hashlib
import io
import json
import sqlite3
import time
import zipfile
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from cybercheck.api import create_app
from cybercheck.auth import SESSION_COOKIE, STATE_COOKIE, digest
from cybercheck.config import Settings
from cybercheck.github import GitHub, GitHubError
from cybercheck.store import Store
from cybercheck.worker import process


class GitHubService:
    def __init__(self):
        self.revoked = set()
        self.requests = []
        self.exchange = None

    def respond(self, request):
        self.requests.append(request)
        path = request.url.path
        if path == "/login/oauth/access_token":
            body = parse_qs(request.content.decode())
            self.exchange = body
            assert not request.url.query
            name = body["code"][0]
            return httpx.Response(200, json={"access_token": "synthetic-user-" + name,
                                            "expires_in": 28800, "token_type": "bearer"})
        if request.url.host == "codeload.github.com":
            assert "authorization" not in request.headers
            archive = io.BytesIO()
            with zipfile.ZipFile(archive, "w") as package:
                package.writestr("project/app.py", "eval(text)\n")
            return httpx.Response(200, content=archive.getvalue())
        token = request.headers.get("authorization", "")
        assert token.startswith("Bearer synthetic-user-")
        name = token.removeprefix("Bearer synthetic-user-")
        if name in self.revoked:
            return httpx.Response(401, json={"message": "synthetic-sensitive-upstream-error"})
        if path == "/user":
            return httpx.Response(200, json={"id": 1 if name == "alice" else 2, "login": name})
        if path == "/user/installations":
            return httpx.Response(200, json={"total_count": 1, "installations": [
                {"id": 50, "account": {"login": "team"}, "suspended_at": None},
            ]})
        if path == "/user/installations/50/repositories":
            entries = [{"id": 10, "full_name": "team/shared", "private": True, "default_branch": "main"}]
            if name == "alice":
                entries.append({"id": 11, "full_name": "team/private", "private": True, "default_branch": "main"})
            return httpx.Response(200, json={"total_count": len(entries), "repositories": entries})
        if path.startswith("/user/installations/"):
            return httpx.Response(404)
        if path in ("/repositories/10", "/repositories/11"):
            if path.endswith("11") and name != "alice":
                return httpx.Response(404)
            return httpx.Response(200, json={"full_name": "team/shared" if path.endswith("10") else "team/private",
                                            "default_branch": "main"})
        if "/commits/" in path:
            return httpx.Response(200, json={"sha": "a" * 40})
        if "/zipball/" in path:
            assert path.endswith("a" * 40)
            return httpx.Response(302, headers={"location": "https://codeload.github.com/team/private/zip/" + "a" * 40})
        raise AssertionError(f"Unexpected GitHub request: {path}")


@pytest.fixture
def environment(tmp_path):
    settings = Settings(api_token="test-operator-" + "x" * 40, data_dir=tmp_path,
                        github_client_id="test-client", github_client_secret="synthetic-client-secret",
                        session_key=Fernet.generate_key().decode(), public_url="http://127.0.0.1:8000",
                        cors_origins=("http://127.0.0.1:5173",))
    service = GitHubService()
    transport = httpx.MockTransport(service.respond)
    app = create_app(settings, auth_transport=transport)
    clients = []

    def client():
        instance = TestClient(app, base_url=settings.public_url)
        clients.append(instance)
        return instance

    yield settings, service, transport, app, client
    for instance in clients:
        instance.close()


def sign_in(client, name="alice"):
    response = client.get("/auth/github/start", follow_redirects=False)
    assert response.status_code == 302
    query = parse_qs(urlsplit(response.headers["location"]).query)
    response = client.get("/auth/github/callback", params={"code": name, "state": query["state"][0]},
                          follow_redirects=False)
    assert response.status_code == 303
    return client.get("/auth/me").json()["csrf_token"]


def queue(client, csrf, repository_id=10):
    return client.post("/api/analyses", headers={"X-CSRF-Token": csrf}, json={
        "repository_id": repository_id, "authorization_confirmed": True,
    })


def test_login_uses_browser_bound_pkce_and_encrypted_expiring_sessions(environment):
    settings, service, _, app, make_client = environment
    client = make_client()
    start = client.get("/auth/github/start", follow_redirects=False)
    query = parse_qs(urlsplit(start.headers["location"]).query)
    assert query["code_challenge_method"] == ["S256"]
    assert query["scope"] == ["offline_access"]
    assert "httponly" in start.headers["set-cookie"].lower()
    callback = client.get("/auth/github/callback", params={"code": "alice", "state": query["state"][0]},
                          follow_redirects=False)
    assert callback.status_code == 303 and callback.headers["location"] == "/app/"
    verifier = service.exchange["code_verifier"][0]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert query["code_challenge"] == [challenge]
    assert service.exchange["redirect_uri"] == [settings.public_url + "/auth/github/callback"]
    assert STATE_COOKIE not in client.cookies
    me = client.get("/auth/me")
    assert me.json()["user"] == {"id": 1, "login": "alice"}
    assert me.json()["mode"] == "github" and me.json()["csrf_token"]
    assert "synthetic-user-alice" not in me.text and "synthetic-client-secret" not in me.text
    assert me.headers["cache-control"] == "no-store" and me.headers["referrer-policy"] == "no-referrer"
    session = client.cookies.get(SESSION_COOKIE)
    with app.state.store.connect() as db:
        saved = dict(db.execute("SELECT * FROM user_sessions").fetchone())
        assert db.execute("SELECT count(*) FROM oauth_states").fetchone()[0] == 0
    assert saved["hash"] == digest(session) and saved["hash"] != session
    assert saved["token"] != "synthetic-user-alice"
    assert Fernet(settings.session_key.encode()).decrypt(saved["token"].encode()) == b"synthetic-user-alice"
    assert 0 < saved["expires_at"] - int(time.time()) <= 28800


def test_state_mismatch_other_browser_and_replay_never_exchange_a_code(environment):
    _, service, _, app, make_client = environment
    client, other = make_client(), make_client()
    start = client.get("/auth/github/start", follow_redirects=False)
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    assert other.get("/auth/github/callback", params={"code": "alice", "state": state}).status_code == 400
    assert service.exchange is None
    assert client.get("/auth/github/callback", params={"code": "alice", "state": "wrong"}).status_code == 400
    assert service.exchange is None
    start = client.get("/auth/github/start", follow_redirects=False)
    used_state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    assert client.get("/auth/github/callback", params={"code": "alice", "state": used_state},
                      follow_redirects=False).status_code == 303
    client.cookies.set(STATE_COOKIE, used_state, domain="127.0.0.1", path="/auth/github")
    calls = len(service.requests)
    assert client.get("/auth/github/callback", params={"code": "alice", "state": used_state}).status_code == 400
    assert len(service.requests) == calls
    start = other.get("/auth/github/start", follow_redirects=False)
    expired_state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    with app.state.store.connect() as db:
        db.execute("UPDATE oauth_states SET expires_at=0")
    assert other.get("/auth/github/callback", params={"code": "alice", "state": expired_state}).status_code == 400
    assert len(service.requests) == calls
    assert other.get("/auth/me").status_code == 401


def test_user_installations_repository_selection_and_revoked_access(environment):
    _, service, _, _, make_client = environment
    alice, bob = make_client(), make_client()
    alice_csrf, bob_csrf = sign_in(alice), sign_in(bob, "bob")
    assert alice.get("/api/github/installations?page=2").json()["page"] == 2
    assert service.requests[-1].url.params["page"] == "2"
    assert alice.get("/api/repositories").status_code == 422
    assert alice.get("/api/repositories?installation_id=51").status_code == 502
    response = alice.get("/api/repositories?installation_id=50&page=3")
    assert response.status_code == 200 and response.json()["page"] == 3
    assert dict(service.requests[-1].url.params) == {"per_page": "100", "page": "3"}
    assert len(response.json()["repositories"]) == 2
    assert len(bob.get("/api/repositories?installation_id=50").json()["repositories"]) == 1
    assert queue(bob, bob_csrf, 11).status_code == 502
    assert queue(alice, alice_csrf, 11).status_code == 202
    service.revoked.add("alice")
    response = alice.get("/api/repositories?installation_id=50")
    assert response.status_code == 502 and "synthetic-sensitive" not in response.text


def test_commit_reference_stays_in_one_url_segment(environment):
    settings, service, transport, _, _ = environment
    github = GitHub(settings, transport, user_token="synthetic-user-alice")

    assert github.resolve(10, "feature/login")[2] == "feature/login"
    assert service.requests[-1].url.raw_path == b"/repos/team/shared/commits/feature%2Flogin"

    with pytest.raises(GitHubError, match="Select a valid Git reference"):
        github.resolve(10, ".")
    assert service.requests[-1].url.path == "/repositories/10"


def test_two_users_have_isolated_history_reports_deletion_and_deduplication(environment):
    _, _, _, app, make_client = environment
    alice, bob = make_client(), make_client()
    alice_csrf, bob_csrf = sign_in(alice), sign_in(bob, "bob")
    first = queue(alice, alice_csrf)
    second = queue(bob, bob_csrf)
    assert first.json()["created"] and second.json()["created"]
    assert first.json()["analysis"]["id"] != second.json()["analysis"]["id"]
    assert not queue(alice, alice_csrf).json()["created"]
    assert "owner" not in first.json()["analysis"]
    assert len(alice.get("/api/analyses").json()["analyses"]) == 1
    location = first.headers["location"]
    assert bob.get(location).status_code == 404
    assert bob.delete(location, headers={"X-CSRF-Token": bob_csrf}).status_code == 404
    assert alice.delete(location, headers={"X-CSRF-Token": alice_csrf}).status_code == 204
    assert len(bob.get("/api/analyses").json()["analyses"]) == 1
    legacy, _ = app.state.store.create(10, "team/shared", "b" * 40, "main", False)
    assert alice.get("/api/analyses/" + legacy["id"]).status_code == 404
    assert bob.get("/api/analyses/" + legacy["id"]).status_code == 404


def test_csrf_origin_logout_expiry_and_operator_token_cannot_bypass_login(environment):
    settings, _, _, app, make_client = environment
    client = make_client()
    assert client.get("/api/analyses", headers={"Authorization": "Bearer " + settings.api_token}).status_code == 401
    csrf = sign_in(client)
    assert queue(client, "wrong").status_code == 403
    assert client.post("/auth/logout").status_code == 403
    assert client.post("/auth/logout", headers={"X-CSRF-Token": csrf, "Origin": "https://evil.invalid"}).status_code == 403
    assert client.post("/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
    assert client.get("/auth/me").status_code == 401
    sign_in(client)
    with app.state.store.connect() as db:
        db.execute("UPDATE user_sessions SET expires_at=0")
    assert client.get("/auth/me").status_code == 401


@pytest.mark.parametrize("revoked", [False, True])
def test_worker_downloads_recorded_sha_as_the_user_and_rechecks_access(environment, monkeypatch, revoked):
    settings, service, transport, app, make_client = environment
    client = make_client()
    response = queue(client, sign_in(client), 11)
    assert response.status_code == 202
    if revoked:
        service.revoked.add("alice")
    monkeypatch.setattr("cybercheck.worker.GitHub", lambda settings, **kwargs: GitHub(settings, transport, **kwargs))
    scanned = []

    def scan(source, working, settings, lookup):
        scanned.append(True)
        assert (source / "app.py").read_text() == "eval(text)\n"
        return [], [{"tool": "test-scanner", "status": "completed", "version": "1.0.0"}]

    monkeypatch.setattr("cybercheck.worker.run_scanners", scan)
    process(app.state.store.claim(), app.state.store, None, settings)
    report = client.get(response.headers["location"]).json()["analysis"]
    assert report["status"] == ("failed" if revoked else "completed")
    assert bool(scanned) is not revoked
    assert report["commit_sha"] == "a" * 40
    assert "synthetic-user" not in json.dumps(report) and "synthetic-sensitive" not in json.dumps(report)
    assert not list(settings.data_dir.glob("analysis-*"))


def test_worker_never_falls_back_to_app_installation_after_user_logout(environment):
    settings, _, _, app, make_client = environment
    client = make_client()
    csrf = sign_in(client)
    response = queue(client, csrf)
    assert client.post("/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204
    process(app.state.store.claim(), app.state.store, None, settings)
    report = app.state.store.get(response.json()["analysis"]["id"], owner="github:1")
    assert report["status"] == "failed" and "signed out" in report["error"]


@pytest.mark.parametrize("payload", [
    {}, {"error": "synthetic-sensitive-upstream-error"}, [],
    {"access_token": "synthetic-user-alice", "token_type": "bearer"},
    {"access_token": "synthetic-user-alice", "token_type": "bearer", "expires_in": True},
    {"access_token": "synthetic\ninvalid", "token_type": "bearer", "expires_in": 28800},
])
def test_invalid_token_responses_fail_closed_without_exposing_provider_content(environment, payload):
    _, _, _, app, make_client = environment
    client = make_client()
    app.state.auth.transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    start = client.get("/auth/github/start", follow_redirects=False)
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    response = client.get("/auth/github/callback", params={"code": "alice", "state": state})
    assert response.status_code == 400
    assert "synthetic-sensitive" not in response.text and "synthetic-user" not in response.text
    assert client.get("/auth/me").status_code == 401
    with app.state.store.connect() as db:
        assert db.execute("SELECT count(*) FROM user_sessions").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM oauth_states").fetchone()[0] == 0


@pytest.mark.parametrize("failure", ["network", "invalid-json", "redirect"])
def test_token_exchange_failures_are_safe_and_not_followed(environment, failure):
    _, _, _, app, make_client = environment
    client = make_client()
    calls = []

    def respond(request):
        calls.append(request)
        if failure == "network":
            raise httpx.ConnectError("synthetic-sensitive-network-error", request=request)
        if failure == "redirect":
            return httpx.Response(302, headers={"location": "https://evil.invalid/"})
        return httpx.Response(200, content=b"synthetic-sensitive-not-json")

    app.state.auth.transport = httpx.MockTransport(respond)
    start = client.get("/auth/github/start", follow_redirects=False)
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    response = client.get("/auth/github/callback", params={"code": "alice", "state": state})
    assert response.status_code == 400
    assert response.json() == {"detail": "GitHub login failed. Start again."}
    assert len(calls) == 1 and calls[0].url.host == "github.com"


def test_https_cookies_cors_and_openapi_session_contract(environment):
    settings, _, transport, _, _ = environment
    settings = replace(settings, api_token="", public_url="https://cybercheck.example")
    with TestClient(create_app(settings, auth_transport=transport), base_url=settings.public_url) as client:
        csrf = sign_in(client)
        cookie = next(cookie for cookie in client.cookies.jar if cookie.name == SESSION_COOKIE)
        assert cookie.secure and cookie.has_nonstandard_attr("HttpOnly")
        assert cookie.get_nonstandard_attr("SameSite") == "lax"
        preflight = client.options("/api/analyses", headers={
            "Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-CSRF-Token,Content-Type",
        })
        assert preflight.status_code == 200
        assert preflight.headers["access-control-allow-credentials"] == "true"
        evil = client.get("/auth/me", headers={"Origin": "https://evil.invalid"})
        assert "access-control-allow-origin" not in evil.headers
        schema = client.get("/openapi.json").json()
        assert schema["components"]["securitySchemes"]["APIKeyCookie"]["name"] == SESSION_COOKIE
        assert any(item["name"] == "X-CSRF-Token" for item in schema["paths"]["/api/analyses"]["post"]["parameters"])
        assert client.post("/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 204


def test_web_jobs_and_strict_repository_consent_are_also_isolated(environment):
    _, _, _, _, make_client = environment
    alice, bob = make_client(), make_client()
    alice_csrf, bob_csrf = sign_in(alice), sign_in(bob, "bob")
    body = {"target_url": "https://example.com/", "authorization_confirmed": True}
    first = alice.post("/api/web-analyses", json=body, headers={"X-CSRF-Token": alice_csrf})
    second = bob.post("/api/web-analyses", json=body, headers={"X-CSRF-Token": bob_csrf})
    assert first.json()["analysis"]["id"] != second.json()["analysis"]["id"]
    assert bob.get(first.headers["location"]).status_code == 404
    for field in ("authorization_confirmed", "dependency_lookup"):
        payload = {"repository_id": 10, "authorization_confirmed": True, field: "true"}
        assert alice.post("/api/analyses", json=payload, headers={"X-CSRF-Token": alice_csrf}).status_code == 422


@pytest.mark.parametrize("change", [
    {"github_client_secret": ""}, {"session_key": "invalid"}, {"cors_origins": ("*",)},
    {"public_url": "http://public.example"}, {"public_url": "https://user:secret@example.com"},
    {"public_url": "https://example.com/path"}, {"public_url": "https://example.com/?key=value"},
])
def test_invalid_oauth_configuration_is_rejected(environment, change):
    settings, *_ = environment
    with pytest.raises(ValueError):
        replace(settings, **change)


def test_owner_migration_keeps_old_history_private_and_durable(tmp_path):
    with sqlite3.connect(tmp_path / "cybercheck.sqlite3") as db:
        db.execute("""CREATE TABLE analyses (
            id TEXT PRIMARY KEY, kind TEXT NOT NULL DEFAULT 'repository', repository_id INTEGER, repository TEXT, commit_sha TEXT,
            requested_ref TEXT, target_url TEXT, status TEXT NOT NULL DEFAULT 'queued', created_at TEXT NOT NULL, started_at TEXT,
            finished_at TEXT, dependency_lookup INTEGER NOT NULL, findings TEXT NOT NULL DEFAULT '[]',
            checks TEXT NOT NULL DEFAULT '[]', requests TEXT NOT NULL DEFAULT '[]',
            limitations TEXT NOT NULL DEFAULT '[]', error TEXT
        )""")
        db.execute("INSERT INTO analyses VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            "existing", "repository", 10, "team/shared", "a" * 40, "main", None, "queued", "now",
            None, None, 0, "[]", "[]", "[]", "[]", None,
        ))
        db.execute("CREATE UNIQUE INDEX one_active_revision ON analyses(repository_id,commit_sha) "
                   "WHERE kind='repository' AND status IN ('queued','running')")
        db.execute("CREATE UNIQUE INDEX one_active_website ON analyses(target_url) "
                   "WHERE kind='web' AND status IN ('queued','running')")
    store = Store(tmp_path)
    assert store.get("existing")["owner"] == "operator"
    assert store.get("existing", owner="github:1") is None
    job, created = store.create(10, "team/shared", "a" * 40, "main", False, owner="github:1")
    assert created and job["id"] != "existing"
    assert Store(tmp_path).get(job["id"], owner="github:1") == job
