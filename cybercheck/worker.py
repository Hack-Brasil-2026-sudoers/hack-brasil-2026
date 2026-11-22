import fcntl
import shutil
import stat
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath

import httpx

from .config import Settings
from .auth import Auth
from .github import GitHub, GitHubError
from .scanners import run_scanners
from .store import Store
from .web import WebError, analyze_web


def extract_archive(archive: Path, target: Path):
    total = 0
    names = set()
    with zipfile.ZipFile(archive) as package:
        entries = package.infolist()
        if not entries or len(entries) > 5000:
            raise ValueError("Archive is empty or contains more than 5,000 entries.")
        root = None
        for entry in entries:
            path = PurePosixPath(entry.filename)
            if path.is_absolute() or ".." in path.parts or "\\" in entry.filename:
                raise ValueError("Archive contains an unsafe path.")
            if not path.parts:
                raise ValueError("Archive contains an empty path.")
            root = root or path.parts[0]
            if path.parts[0] != root:
                raise ValueError("Archive must contain a single root directory.")
            relative = Path(*path.parts[1:])
            mode = entry.external_attr >> 16
            if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)):
                raise ValueError("Links and special files are not allowed.")
            if entry.is_dir():
                continue
            if not relative.parts or relative in names:
                raise ValueError("Invalid or duplicate archive entry.")
            names.add(relative)
            if entry.file_size > 2 * 1024 * 1024:
                raise ValueError("Individual file exceeds 2 MiB.")
            total += entry.file_size
            if total > 100 * 1024 * 1024:
                raise ValueError("Uncompressed content exceeds 100 MiB.")
            output = target / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            with package.open(entry) as src, output.open("xb") as dst:
                shutil.copyfileobj(src, dst, 65536)
            output.chmod(0o600)


def process(analysis, store: Store, github: GitHub, settings: Settings):
    try:
        if analysis["kind"] == "web":
            report = analyze_web(analysis["target_url"], authorization_confirmed=True)
            error = next((check["error"] for check in report["checks"] if check.get("error")), None)
            store.finish(analysis["id"], report["status"], report["findings"], report["checks"], error,
                         requests=report["requests"], limitations=report["limitations"])
            return
        with tempfile.TemporaryDirectory(prefix="analysis-", dir=store.directory) as tmp:
            working = Path(tmp)
            archive = working / "source.zip"
            source = working / "source"
            source.mkdir()
            repository_github = github
            if analysis.get("owner", "operator") != "operator":
                token = Auth(settings, store).token_for_owner(analysis["owner"])
                repository_github = GitHub(settings, user_token=token)
            repository_github.download(analysis, archive)
            extract_archive(archive, source)
            archive.unlink()
            findings, checks = run_scanners(source, working, settings, analysis["dependency_lookup"])
            statuses = [c["status"] for c in checks]
            status = "completed" if all(s == "completed" for s in statuses) else (
                "partial" if any(s in ("completed", "partial") for s in statuses) else "failed")
        # Finalize only after discarding source code and raw outputs.
        store.finish(analysis["id"], status, findings, checks, limitations=[
            "Python code checks use selected Bandit patterns without full data-flow analysis. "
            "Assignment aliases and dynamically selected calls may be missed. "
            "Findings require input-trust and deployment-context review; no findings does not establish safety.",
        ])
    except GitHubError as exc:
        store.finish(analysis["id"], "failed", error=str(exc))
    except WebError as exc:
        store.finish(analysis["id"], "failed", error=str(exc))
    except (ValueError, zipfile.BadZipFile):
        store.finish(analysis["id"], "failed", error="Archive is invalid or exceeds the MVP limits.")
    except (OSError, httpx.HTTPError):
        store.finish(analysis["id"], "failed", error="Network or storage failure during analysis.")
    except Exception:
        # Unexpected errors must not persist content or tokens from exceptions.
        store.finish(analysis["id"], "failed", error="Unexpected worker failure. Request a new analysis.")


def run(settings: Settings, once=False):
    store = Store(settings.data_dir)
    with (store.directory / "worker.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("A worker is already running for this data directory.")
        # Once the lock is acquired, no previous worker should still be active here.
        for old in store.directory.glob("analysis-*"):
            if old.is_dir() and not old.is_symlink():
                shutil.rmtree(old)
        store.recover()
        github = GitHub(settings)
        while True:
            analysis = store.claim()
            if analysis:
                process(analysis, store, github, settings)
            if once:
                return
            time.sleep(2)
