import json
import stat
import zipfile
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from cybercheck.api import create_app
from cybercheck.config import Settings
from cybercheck.github import GitHub, GitHubError
from cybercheck.scanners import parse_bandit, parse_betterleaks, parse_osv, run_scanners
from cybercheck.store import Store
from cybercheck.worker import extract_archive, process


TOKEN = "local-test-token-" + "x" * 40
SHA = "a" * 40
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture
def settings(tmp_path):
    return Settings(api_token=TOKEN, data_dir=tmp_path / "data")


class FakeGitHub:
    def repositories(self, page):
        return {"page": page, "total_count": 1, "repositories": [
            {"id": 10, "full_name": "team/project", "private": True, "default_branch": "main"}]}

    def resolve(self, repository_id, reference):
        if repository_id != 10:
            raise GitHubError("Acesso não autorizado.")
        return "team/project", SHA, reference or "main"

    def download(self, analysis, destination):
        with zipfile.ZipFile(destination, "w") as archive:
            archive.writestr("project/sample.py", "result = eval(input())  # nosec\n")


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings, FakeGitHub())) as client:
        yield client


def start(client, **changes):
    body = {"repository_id": 10, "authorization_confirmed": True}
    body.update(changes)
    return client.post("/api/analyses", headers=HEADERS, json=body)


def test_authentication_and_authorization(client):
    assert client.get("/health").status_code == 200
    assert client.get("/api/analyses").status_code == 401
    assert client.get("/api/repositories", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert start(client, authorization_confirmed=False).status_code == 422
    assert start(client, repository_id=11).status_code == 502
    assert client.get("/api/analyses", headers=HEADERS).json() == {"analyses": []}


def test_api_records_commit_deduplicates_and_deletes(client):
    response = start(client)
    assert response.status_code == 202
    analysis = response.json()["analysis"]
    assert analysis["commit_sha"] == SHA
    assert analysis["created_at"].endswith("+00:00")
    assert analysis["status"] == "queued"
    assert start(client).json()["created"] is False
    report_url = response.headers["location"]
    assert client.get(report_url, headers=HEADERS).json()["groups"] == {}
    assert client.delete(report_url, headers=HEADERS).status_code == 204
    assert client.get(report_url, headers=HEADERS).status_code == 404


def test_input_validation_and_running_delete(client):
    assert start(client, repository_id=-1).status_code == 422
    assert start(client, reference="bad\nref").status_code == 422
    assert start(client, unexpected="value").status_code == 422
    response = start(client)
    store = client.app.state.store
    assert store.claim()["id"] == response.json()["analysis"]["id"]
    assert client.delete(response.headers["location"], headers=HEADERS).status_code == 409


def test_queue_recovers_interrupted_jobs(settings):
    store = Store(settings.data_dir)
    job, _ = store.create(10, "team/project", SHA, "main", False)
    assert store.claim()["id"] == job["id"]
    assert store.claim() is None
    store.recover()
    assert store.get(job["id"])["status"] == "failed"
    assert store.get(job["id"])["finished_at"]
    assert store.path.stat().st_mode & 0o077 == 0


@pytest.mark.parametrize("name", ["root/../outside", "/absolute", "root/../../outside", "root\\outside"])
def test_archive_rejects_traversal(tmp_path, name):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(name, "bad")
    target = tmp_path / "source"
    target.mkdir()
    with pytest.raises(ValueError):
        extract_archive(archive, target)
    assert not (tmp_path / "outside").exists()


def test_archive_rejects_links_duplicates_and_oversized_files(tmp_path):
    archive = tmp_path / "bad.zip"
    info = zipfile.ZipInfo("root/link")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr(info, "/etc/passwd")
    target = tmp_path / "source"
    target.mkdir()
    with pytest.raises(ValueError):
        extract_archive(archive, target)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("root/big.txt", b"x" * (2 * 1024 * 1024 + 1))
    with pytest.raises(ValueError):
        extract_archive(archive, target)


def test_betterleaks_never_persists_secret_or_match(tmp_path):
    secret = "synthetic-sensitive-" + "value-not-a-real-credential"
    output = parse_betterleaks([{"RuleID": "generic-api-key", "File": "config.py", "StartLine": 3,
                                "Secret": secret, "Match": secret, "Description": secret}], tmp_path)
    assert secret not in json.dumps(output)
    assert output[0]["priority"] == "review"
    assert output[0]["evidence"]["validated"] is False


def test_bandit_priority_is_not_confirmation(tmp_path):
    row = {"test_id": "B608", "filename": str(tmp_path / "db.py"), "line_number": 9,
           "issue_severity": "HIGH", "issue_confidence": "LOW", "code": "secret-code"}
    findings = parse_bandit({"results": [row]}, tmp_path)
    assert findings[0]["priority"] == "review"
    assert findings[0]["status"] == "potential"
    assert "secret-code" not in json.dumps(findings)
    row["filename"] = "/outside.py"
    with pytest.raises(ValueError):
        parse_bandit({"results": [row]}, tmp_path)


def test_osv_includes_fixed_versions_without_claiming_exploitability(tmp_path):
    data = {"results": [{"source": {"path": str(tmp_path / "requirements.txt")}, "packages": [{
        "package": {"name": "example", "version": "1.0", "ecosystem": "PyPI"},
        "vulnerabilities": [{"id": "PYSEC-TEST", "database_specific": {"severity": "HIGH"},
                             "affected": [{"ranges": [{"events": [{"introduced": "0"}, {"fixed": "2.0"}]}]}]}],
    }]}]}
    findings = parse_osv(data, tmp_path)
    assert findings[0]["evidence"]["fixed_versions"] == ["2.0"]
    assert findings[0]["confidence"] == "version_match"
    assert findings[0]["status"] == "potential"


def test_worker_partial_and_cleanup(settings):
    store = Store(settings.data_dir)
    job, _ = store.create(10, "team/project", SHA, "main", False)
    process(store.claim(), store, FakeGitHub(), settings)
    report = store.get(job["id"])
    assert report["status"] == "partial"
    assert any(f["rule_id"] == "B307" for f in report["findings"])
    assert next(c for c in report["checks"] if c["tool"] == "osv-scanner")["status"] == "skipped"
    assert not list(store.directory.glob("analysis-*"))
    assert "eval(input())" not in json.dumps(report)


def test_worker_revoked_access_and_failure_cleanup(settings):
    class Revoked(FakeGitHub):
        def download(self, analysis, destination):
            raise GitHubError("Acesso revogado.")
    store = Store(settings.data_dir)
    job, _ = store.create(10, "team/project", SHA, "main", False)
    process(store.claim(), store, Revoked(), settings)
    assert store.get(job["id"])["status"] == "failed"
    assert not list(store.directory.glob("analysis-*"))


def test_real_bandit_finds_unsafe_and_not_corrected_code(tmp_path, settings):
    source = tmp_path / "source"
    source.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    path = source / "sample.py"
    path.write_text("eval(input()) # nosec\n")
    findings, checks = run_scanners(source, work, settings, False)
    assert any(f["rule_id"] == "B307" for f in findings)
    assert checks[0]["status"] == "completed"
    path.write_text("value = int(input())\n")
    findings, checks = run_scanners(source, work, settings, False)
    assert not any(f["rule_id"] == "B307" for f in findings)


def test_download_does_not_forward_token_or_follow_untrusted_redirect(settings, tmp_path, monkeypatch):
    def respond(request):
        if request.url.host == "api.github.com" and request.url.path == "/repositories/10":
            return httpx.Response(200, json={"full_name": "team/project"})
        if request.url.host == "api.github.com":
            return httpx.Response(302, headers={"location": "https://evil.invalid/repo.zip"})
        raise AssertionError("Não deve acessar o destino externo")
    github = GitHub(settings, transport=httpx.MockTransport(respond))
    monkeypatch.setattr(github, "installation_token", lambda repository_id: "never-leak-this-token")
    with pytest.raises(GitHubError):
        github.download({"repository_id": 10, "repository": "team/project", "commit_sha": SHA}, tmp_path / "a.zip")


def test_download_codeload_without_auth_header(settings, tmp_path, monkeypatch):
    def respond(request):
        if request.url.path == "/repositories/10":
            return httpx.Response(200, json={"full_name": "team/project"})
        if request.url.host == "api.github.com":
            assert request.headers["authorization"] == "Bearer test-only"
            return httpx.Response(302, headers={"location": "https://codeload.github.com/team/project/zip/" + SHA})
        assert "authorization" not in request.headers
        return httpx.Response(200, content=b"archive")
    github = GitHub(settings, transport=httpx.MockTransport(respond))
    monkeypatch.setattr(github, "installation_token", lambda repository_id: "test-only")
    dest = tmp_path / "archive.zip"
    github.download({"repository_id": 10, "repository": "team/project", "commit_sha": SHA}, dest)
    assert dest.read_bytes() == b"archive"
