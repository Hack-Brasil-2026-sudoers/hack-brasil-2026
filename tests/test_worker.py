import socket

from cybercheck.config import Settings
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
