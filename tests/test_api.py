import pytest
from fastapi.testclient import TestClient

from cybercheck.api import create_app
from cybercheck.config import Settings
from cybercheck.scanners import finding


TOKEN = "test-operator-" + "x" * 40
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        pytest.fail("Enqueueing a web analysis must not resolve DNS or request the website")
    monkeypatch.setattr("cybercheck.web.socket.getaddrinfo", no_network)
    settings = Settings(api_token=TOKEN, data_dir=tmp_path, cors_origins=("http://localhost:5173",))
    with TestClient(create_app(settings)) as client:
        yield client


def enqueue(client, **changes):
    payload = {"target_url": "https://EXAMPLE.com:443", "authorization_confirmed": True}
    payload.update(changes)
    return client.post("/api/web-analyses", json=payload, headers=HEADERS)


def test_web_queue_contract_authentication_deduplication_and_history(client):
    assert client.post("/api/web-analyses", json={}).status_code == 401
    assert enqueue(client, authorization_confirmed=False).status_code == 422
    assert enqueue(client, authorization_confirmed="true").status_code == 422
    response = enqueue(client)
    assert response.status_code == 202
    job = response.json()["analysis"]
    assert job["kind"] == "web" and job["target_url"] == "https://example.com/"
    assert job["commit_sha"] is None and job["repository"] is None
    assert job["status"] == "queued" and job["requests"] == []
    assert response.json()["created"] is True
    duplicate = enqueue(client, target_url="https://example.com/").json()
    assert duplicate["created"] is False and duplicate["analysis"]["id"] == job["id"]
    location = response.headers["location"]
    assert client.get(location, headers=HEADERS).json() == {"analysis": job, "groups": {}}
    assert client.get("/api/analyses", headers=HEADERS).json() == {"analyses": [job]}
    assert client.delete(location, headers=HEADERS).status_code == 204
    assert client.get(location, headers=HEADERS).status_code == 404


@pytest.mark.parametrize("target", ["file:///etc/passwd", "https://user:password@example.com/",
                                    "https://example.com/?token=private", "https://example.com:8443/",
                                    "https://example.com/#private", "not a URL"])
def test_invalid_web_targets_do_not_echo_raw_input_or_enter_queue(client, target):
    response = enqueue(client, target_url=target)
    assert response.status_code == 422
    assert target not in response.text
    assert all(set(issue) == {"loc", "msg", "type"} for issue in response.json()["detail"])
    assert client.app.state.store.list() == []


def test_shared_capacity_and_running_delete_contract(client):
    for index in range(20):
        assert enqueue(client, target_url=f"https://example.com/{index}").status_code == 202
    assert enqueue(client).status_code == 429
    assert enqueue(client, unexpected="value").status_code == 422
    claimed = client.app.state.store.claim()
    assert client.delete(f"/api/analyses/{claimed['id']}", headers=HEADERS).status_code == 409
    assert client.get("/api/analyses/not-a-uuid", headers=HEADERS).status_code == 422


def test_openapi_publishes_responses_and_cors_exposes_location(client):
    schema = client.get("/openapi.json").json()
    for path in ("/api/analyses", "/api/web-analyses"):
        operation = schema["paths"][path]["post"]
        assert operation["responses"]["202"]["content"]["application/json"]["schema"]["$ref"].endswith("/AnalysisAccepted")
        assert operation["responses"]["422"]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorResponse")
        assert operation["security"] == [{"HTTPBearer": []}]
    assert "AnalysisReport" in schema["components"]["schemas"]
    response = client.post("/api/web-analyses", headers={**HEADERS, "Origin": "http://localhost:5173"},
                           json={"target_url": "https://example.com/", "authorization_confirmed": True})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "Location" in response.headers["access-control-expose-headers"]


def test_repository_request_and_completed_report_keep_existing_fields(tmp_path):
    class GitHubStub:
        def resolve(self, repository_id, reference):
            assert repository_id == 123 and reference == "main"
            return "team/project", "a" * 40, reference

    settings = Settings(api_token=TOKEN, data_dir=tmp_path)
    with TestClient(create_app(settings, GitHubStub())) as client:
        response = client.post("/api/analyses", headers=HEADERS, json={
            "repository_id": 123, "reference": "main", "authorization_confirmed": True, "dependency_lookup": True,
        })
        assert response.status_code == 202
        job = response.json()["analysis"]
        assert job["kind"] == "repository" and job["target_url"] is None
        assert job["commit_sha"] == "a" * 40 and job["dependency_lookup"] is True
        issue = finding("bandit", "B307", "unsafe_execution", "Use of eval", "app.py", 3,
                        "high", "high", "Avoid executing input.", {"rule": "B307"})
        client.app.state.store.finish(job["id"], "completed", [issue], [
            {"tool": "bandit", "version": "1.9.4", "status": "completed", "error": None}])
        report = client.get(response.headers["location"], headers=HEADERS).json()
        assert report["groups"] == {"unsafe_execution": [issue]}
        assert report["analysis"]["findings"] == [issue]
        assert report["analysis"]["checks"][0]["version"] == "1.9.4"
        assert report["analysis"]["requests"] == [] and report["analysis"]["limitations"] == []
