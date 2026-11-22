import json
import socket
import zipfile
from pathlib import Path

from cybercheck.config import Settings
from cybercheck.scanners import run_command
from cybercheck.store import Store
from cybercheck.worker import process, run


def test_worker_revalidates_web_destination_without_github_access(tmp_path, monkeypatch):
    settings = Settings(api_token="x" * 40, data_dir=tmp_path)
    store = Store(tmp_path)
    job, _ = store.create_web("https://example.com/")
    monkeypatch.setattr("cybercheck.web.socket.getaddrinfo", lambda *a, **kw: [
        (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 443))])

    def no_connection(*args, **kwargs):
        raise AssertionError("Blocked destinations must not be contacted")
    monkeypatch.setattr("cybercheck.web.socket.create_connection", no_connection)
    run(settings, once=True)
    report = store.get(job["id"])
    assert report["status"] == "failed"
    assert "destinations are blocked" in report["error"]
    assert report["checks"][0]["status"] == "failed"
    assert report["requests"] == [] and report["limitations"]
    assert report["started_at"] and report["finished_at"]


def test_unexpected_web_failure_does_not_leak_exception_or_stop_next_job(tmp_path, monkeypatch):
    settings = Settings(api_token="x" * 40, data_dir=tmp_path)
    store = Store(tmp_path)
    first, _ = store.create_web("https://example.com/first")
    second, _ = store.create_web("https://example.com/second")

    def analyze(url, **kwargs):
        if url.endswith("first"):
            raise RuntimeError("synthetic-sensitive-exception")
        return {"status": "completed", "findings": [], "checks": [], "requests": [], "limitations": []}
    monkeypatch.setattr("cybercheck.worker.analyze_web", analyze)
    process(store.claim(), store, None, settings)
    assert "synthetic-sensitive" not in store.get(first["id"])["error"]
    assert store.get(first["id"])["status"] == "failed"
    process(store.claim(), store, None, settings)
    assert store.get(second["id"])["status"] == "completed"


def test_repository_worker_keeps_code_findings_when_dependency_output_is_invalid(tmp_path, monkeypatch):
    class Repository:
        def download(self, analysis, destination):
            assert analysis["commit_sha"] == "a" * 40
            with zipfile.ZipFile(destination, "w") as archive:
                archive.writestr("project/app.py", 'eval("synthetic-private-source")  # nosec\n')

    def command(args, cwd, timeout):
        if "bandit" in args:
            return run_command(args, cwd, timeout)
        tool = Path(args[0]).name
        if "--version" in args or "version" in args:
            return 0, b"2.7.1" if tool == "osv-scanner" else b"1.10.1"
        if tool == "betterleaks":
            (cwd / "secrets.json").write_text("[]")
            return 0, b""
        return 0, b'{"results": [null]}'

    monkeypatch.setattr("cybercheck.scanners.run_command", command)
    settings = Settings(api_token="x" * 40, data_dir=tmp_path)
    store = Store(tmp_path)
    job, _ = store.create(123, "team/project", "a" * 40, "main", True)
    process(store.claim(), store, Repository(), settings)
    report = store.get(job["id"])
    assert report["status"] == "partial"
    assert report["commit_sha"] == "a" * 40
    assert report["started_at"] and report["finished_at"]
    assert any(item["rule_id"] == "B307" for item in report["findings"])
    assert {check["tool"]: check["status"] for check in report["checks"]} == {
        "bandit": "completed", "osv-scanner": "failed", "betterleaks": "completed",
    }
    assert "synthetic-private-source" not in json.dumps(report)
    assert any("without full data-flow analysis" in item for item in report["limitations"])
    assert any("Assignment aliases" in item for item in report["limitations"])
    assert not list(tmp_path.glob("analysis-*"))
