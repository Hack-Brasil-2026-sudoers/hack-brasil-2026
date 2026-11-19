import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from cybercheck.store import QueueFull, Store


def test_migrates_existing_repository_history_without_losing_reports(tmp_path):
    database = tmp_path / "cybercheck.sqlite3"
    with sqlite3.connect(database) as db:
        db.execute("""CREATE TABLE analyses (
            id TEXT PRIMARY KEY, repository_id INTEGER NOT NULL, repository TEXT NOT NULL,
            commit_sha TEXT NOT NULL, requested_ref TEXT NOT NULL, status TEXT NOT NULL,
            created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT,
            dependency_lookup INTEGER NOT NULL, findings TEXT NOT NULL, checks TEXT NOT NULL, error TEXT
        )""")
        db.execute("CREATE UNIQUE INDEX one_active_revision ON analyses(repository_id, commit_sha) "
                   "WHERE status IN ('queued','running')")
        db.execute("INSERT INTO analyses VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            "existing", 10, "team/project", "a" * 40, "main", "queued", "2026-11-18T12:00:00+00:00",
            None, None, 1, json.dumps([{"rule_id": "B307"}]), "[]", None,
        ))
    store = Store(tmp_path)
    original = store.get("existing")
    assert original["kind"] == "repository"
    assert original["commit_sha"] == "a" * 40
    assert original["findings"] == [{"rule_id": "B307"}]
    assert original["dependency_lookup"] is True
    assert original["target_url"] is None
    assert store.create(10, "team/project", "a" * 40, "main", True)[1] is False
    website, _ = store.create_web("https://example.com/")
    assert website["repository_id"] is None
    assert Store(tmp_path).get("existing") == original
    with store.connect() as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_concurrent_web_requests_share_one_durable_job(tmp_path):
    store = Store(tmp_path)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: store.create_web("https://example.com/"), range(8)))
    assert len({job["id"] for job, _ in results}) == 1
    assert sum(created for _, created in results) == 1
    job = store.claim()
    assert not store.delete(job["id"])
    store.finish(job["id"], "completed", requests=[{"url": job["target_url"], "status_code": 200, "tls": None}],
                 limitations=["Unauthenticated GET only."])
    persisted = Store(tmp_path).get(job["id"])
    assert persisted["requests"][0]["status_code"] == 200
    assert persisted["limitations"] == ["Unauthenticated GET only."]
    assert store.create_web(job["target_url"])[1] is True
    assert store.delete(job["id"])


def test_repository_and_web_jobs_share_capacity_and_recovery(tmp_path):
    store = Store(tmp_path)
    for index in range(10):
        store.create(10, "team/project", f"{index:040x}", "main", False)
        store.create_web(f"https://example.com/{index}")
    assert store.create_web("https://example.com/0")[1] is False
    with pytest.raises(QueueFull):
        store.create_web("https://example.com/overflow")
    with pytest.raises(QueueFull):
        store.create(10, "team/project", "f" * 40, "main", False)
    for _ in range(20):
        store.claim()
    store.recover()
    assert all(job["status"] == "failed" and job["finished_at"] for job in store.list())
