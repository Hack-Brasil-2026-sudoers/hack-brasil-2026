import fcntl
import shutil
import tempfile
import time
import logging
from pathlib import Path

import httpx

from .archives import ArchiveError, extract_archive
from .config import Settings
from .auth import Auth
from .github import GitHub, GitHubError
from .scanners import run_scanners
from .store import Store
from .web import WebError, analyze_web


logger = logging.getLogger(__name__)


def process(analysis, store: Store, github: GitHub, settings: Settings):
    stage = "authorization"
    def progress(value):
        nonlocal stage
        stage = value
        logger.info("analysis=%s stage=%s", analysis["id"], stage)
    try:
        progress("authorization")
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
            progress("download")
            repository_github.download(analysis, archive)
            progress("extraction")
            extract_archive(archive, source)
            archive.unlink()
            progress("scanners")
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
        progress(status)
    except ArchiveError as exc:
        logger.warning("analysis=%s stage=%s error=%s", analysis["id"], stage, exc.code)
        store.finish(analysis["id"], "failed", error=f"{stage.capitalize()} failed [{exc.code}]: {exc}",
                     limitations=[f"Preparation stopped during {stage}; no security scanners ran."])
    except httpx.RemoteProtocolError:
        store.finish(analysis["id"], "failed", error="Archive download was interrupted or incomplete. Retry the analysis.")
    except httpx.TimeoutException:
        store.finish(analysis["id"], "failed", error=f"Network timeout during {stage}. Retry the analysis.")
    except GitHubError as exc:
        store.finish(analysis["id"], "failed", error=str(exc))
    except WebError as exc:
        store.finish(analysis["id"], "failed", error=str(exc))
    except ValueError:
        store.finish(analysis["id"], "failed", error=f"Invalid data during {stage}. No complete assessment is available.")
    except OSError:
        store.finish(analysis["id"], "failed", error=f"Local storage or file access failed during {stage}. Check available disk space and permissions.")
    except httpx.HTTPError:
        store.finish(analysis["id"], "failed", error=f"GitHub connection failed during {stage}. Retry when the connection is available.")
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
