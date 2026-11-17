import hashlib
import io
import json
import sys
from pathlib import Path

import pytest

from cybercheck.config import Settings
from cybercheck.github import GitHub
from cybercheck.scanners import ScannerError, run_command
from cybercheck.store import QueueFull, Store
from scripts.install_scanners import install


def test_scanner_does_not_inherit_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "synthetic-do-not-inherit")
    monkeypatch.setenv("BETTERLEAKS_CONFIG_TOML", "unsafe-config")
    monkeypatch.setenv("BETTERLEAKS_VALIDATE", "true")
    code, output = run_command([sys.executable, "-c", "import os,json; print(json.dumps(dict(os.environ)))"], tmp_path, 5)
    env = json.loads(output)
    assert code == 0
    assert "GITHUB_TOKEN" not in env
    assert "BETTERLEAKS_CONFIG_TOML" not in env
    assert "BETTERLEAKS_VALIDATE" not in env
    assert env["HOME"] == str(tmp_path)


def test_scanner_timeout(tmp_path):
    with pytest.raises(ScannerError, match="Time limit"):
        run_command([sys.executable, "-c", "import time; time.sleep(10)"], tmp_path, 0.1)


def test_queue_limit(tmp_path):
    store = Store(tmp_path / "data")
    for number in range(20):
        store.create(10, "team/project", f"{number:040x}", "main", False)
    with pytest.raises(QueueFull):
        store.create(10, "team/project", "f" * 40, "main", False)


def test_installation_token_is_restricted_and_jwt_is_not_persisted(tmp_path, monkeypatch):
    import httpx
    import cybercheck.github
    key = tmp_path / "test-key.pem"
    key.write_text("synthetic-placeholder-not-a-real-key")
    monkeypatch.setattr(cybercheck.github.jwt, "encode", lambda *a, **kw: "test-jwt")
    def respond(request):
        assert request.url.path == "/app/installations/456/access_tokens"
        assert request.headers["Authorization"] == "Bearer test-jwt"
        assert json.loads(request.content) == {"repository_ids": [123], "permissions": {"contents": "read", "metadata": "read"}}
        return httpx.Response(201, json={"token": "test-installation-token"})
    github = GitHub(Settings(api_token="x" * 40, app_id="12", installation_id="456", private_key_path=str(key)),
                    transport=httpx.MockTransport(respond))
    assert github.installation_token(123) == "test-installation-token"


def test_installer_rejects_checksum_without_replacing_binary(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.install_scanners.urlopen", lambda *a, **kw: io.BytesIO(b"bad-download"))
    (tmp_path / "scanner").write_bytes(b"original")
    tool = {"name": "scanner", "url": "https://example.invalid/scanner", "sha256": hashlib.sha256(b"expected").hexdigest()}
    with pytest.raises(ValueError, match="SHA-256"):
        install(tool, tmp_path)
    assert (tmp_path / "scanner").read_bytes() == b"original"
