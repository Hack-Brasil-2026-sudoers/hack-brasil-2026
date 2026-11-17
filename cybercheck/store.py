import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def now():
    return datetime.now(timezone.utc).isoformat()


class QueueFull(Exception):
    pass


class Store:
    def __init__(self, directory: Path):
        self.directory = directory.resolve()
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.path = self.directory / "cybercheck.sqlite3"
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id TEXT PRIMARY KEY,
                    repository_id INTEGER NOT NULL,
                    repository TEXT NOT NULL,
                    commit_sha TEXT NOT NULL,
                    requested_ref TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'queued',
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    dependency_lookup INTEGER NOT NULL,
                    findings TEXT NOT NULL DEFAULT '[]',
                    checks TEXT NOT NULL DEFAULT '[]',
                    error TEXT
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_active_revision
                ON analyses(repository_id, commit_sha)
                WHERE status IN ('queued', 'running');
            """)
        self.path.chmod(0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def decode(row):
        if row is None:
            return None
        result = dict(row)
        result["findings"] = json.loads(result["findings"])
        result["checks"] = json.loads(result["checks"])
        result["dependency_lookup"] = bool(result["dependency_lookup"])
        return result

    def create(self, repository_id, repository, commit_sha, requested_ref, lookup):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT * FROM analyses WHERE repository_id=? AND commit_sha=? "
                "AND status IN ('queued','running')", (repository_id, commit_sha)
            ).fetchone()
            if existing:
                return self.decode(existing), False
            if db.execute("SELECT count(*) FROM analyses WHERE status IN ('queued','running')").fetchone()[0] >= 20:
                raise QueueFull
            identity = str(uuid4())
            db.execute(
                "INSERT INTO analyses(id,repository_id,repository,commit_sha,requested_ref,"
                "created_at,dependency_lookup) VALUES(?,?,?,?,?,?,?)",
                (identity, repository_id, repository, commit_sha, requested_ref, now(), lookup),
            )
            row = db.execute("SELECT * FROM analyses WHERE id=?", (identity,)).fetchone()
        return self.decode(row), True

    def get(self, identity):
        with self.connect() as db:
            return self.decode(db.execute("SELECT * FROM analyses WHERE id=?", (identity,)).fetchone())

    def list(self, limit=50, offset=0):
        with self.connect() as db:
            return [self.decode(row) for row in db.execute(
                "SELECT * FROM analyses ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset)
            )]

    def claim(self):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT id FROM analyses WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
            if not row:
                return None
            db.execute("UPDATE analyses SET status='running', started_at=? WHERE id=?", (now(), row["id"]))
            return self.decode(db.execute("SELECT * FROM analyses WHERE id=?", (row["id"],)).fetchone())

    def finish(self, identity, status, findings=(), checks=(), error=None):
        with self.connect() as db:
            db.execute(
                "UPDATE analyses SET status=?,finished_at=?,findings=?,checks=?,error=? WHERE id=?",
                (status, now(), json.dumps(findings), json.dumps(checks), error, identity),
            )

    def recover(self):
        with self.connect() as db:
            db.execute(
                "UPDATE analyses SET status='failed',finished_at=?,error=? WHERE status='running'",
                (now(), "Worker interrupted. Request a new analysis."),
            )

    def delete(self, identity):
        with self.connect() as db:
            return db.execute(
                "DELETE FROM analyses WHERE id=? AND status != 'running'", (identity,)
            ).rowcount > 0
