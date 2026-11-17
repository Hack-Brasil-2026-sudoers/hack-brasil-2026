import json

import pytest

from cybercheck.config import Settings
from cybercheck.scanners import ScannerError, run_scanners


@pytest.mark.parametrize("message,expected", [
    ("No package sources found, --help for usage information.", "skipped"),
    ("Unexpected scanner error", "failed"),
])
def test_osv_missing_sources_is_distinct_from_other_errors(tmp_path, monkeypatch, message, expected):
    source = tmp_path / "source"
    source.mkdir()
    working = tmp_path / "work"
    working.mkdir()

    def command(args, cwd, timeout):
        (cwd / "stderr").write_text("")
        if args[0] == "test-osv":
            if "--version" in args:
                return 0, b"osv-scanner version: 2.7.1"
            (cwd / "stderr").write_text(message)
            return 128, b""
        if "bandit" in args:
            return (0, b"bandit 1.9.4") if "--version" in args else (0, json.dumps({"results": []}).encode())
        raise ScannerError("Ferramenta ausente no teste")

    monkeypatch.setattr("cybercheck.scanners.run_command", command)
    _, checks = run_scanners(source, working, Settings(api_token="x" * 40, osv_bin="test-osv"), True)
    check = next(c for c in checks if c["tool"] == "osv-scanner")
    assert check["status"] == expected
    if expected == "skipped":
        assert "dependências não foram avaliadas" in check["error"]
