import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from cybercheck import web_tools
from cybercheck.web import WebError


def zap_report():
    return {"site": [{"@name": "http://lab-site:8080", "alerts": [{
        "pluginid": "10021", "riskcode": "1", "confidence": "2",
        "name": "Missing content type protection", "solution": "<p>Use nosniff.</p>",
        "instances": [{"uri": "http://lab-site:8080/details?token=synthetic-private-value",
                       "attack": "synthetic-private-value", "evidence": "synthetic-private-value"}],
    }]}]}


def tls_report():
    return [{"id": "cert_chain_of_trust", "severity": "HIGH", "finding": "Self-signed certificate"},
            {"id": "TLS1_3", "severity": "OK", "finding": "offered"}]


def test_zap_normalization_omits_raw_matches_queries_and_html():
    results = web_tools.parse_zap(zap_report())
    assert len(results) == 1
    item = results[0]
    assert item["tool"] == "zap" and item["rule_id"] == "10021"
    assert item["recommendation"] == "Use nosniff."
    assert item["evidence"]["paths"] == ["/details"]
    assert "synthetic-private-value" not in json.dumps(results)
    assert item["status"] == "potential" and "score" not in item


@pytest.mark.parametrize("target", ["https://outside.example", "http://lab-site:9000"])
def test_zap_rejects_reports_for_other_targets(target):
    data = zap_report()
    data["site"][0]["@name"] = target
    with pytest.raises(ValueError):
        web_tools.parse_zap(data)


def test_tls_warnings_are_coverage_limitations_not_vulnerabilities():
    rows = tls_report() + [{"id": "certificate_lookup", "severity": "WARN", "finding": "lookup unavailable"}]
    results, partial = web_tools.parse_testssl(rows)
    assert partial and len(results) == 1
    assert results[0]["rule_id"] == "cert_chain_of_trust"
    assert results[0]["severity"] == "high"


@pytest.mark.parametrize("data", [None, [], {}])
def test_invalid_tls_reports_are_rejected(data):
    with pytest.raises(ValueError):
        web_tools.parse_testssl(data)


def test_report_size_limit(tmp_path):
    path = tmp_path / "too-large.json"
    with path.open("wb") as stream:
        stream.truncate(web_tools.MAX_REPORT_BYTES + 1)
    with pytest.raises(ValueError, match="size limit"):
        web_tools.read_report(path)


def test_authorization_is_required_before_invoking_runtime(monkeypatch):
    monkeypatch.setattr(web_tools.subprocess, "run", lambda *a, **kw: pytest.fail("Unauthorized invocation"))
    with pytest.raises(WebError, match="authorization"):
        web_tools.run_lab()


def test_all_web_images_are_locked_to_digests():
    images = web_tools.locked_images()
    assert set(images) == {"site", "zap", "testssl"}
    assert all("@sha256:" in spec["image"] and spec["version"] != "pending-verification"
               for spec in images.values())


@pytest.fixture
def simulated_runtime(monkeypatch):
    calls = []
    mode = {"zap": "success", "site": "success", "network": "internal"}
    images = web_tools.locked_images()
    monkeypatch.setattr(web_tools.shutil, "which", lambda name: "/usr/bin/podman")
    monkeypatch.setattr(web_tools, "create_certificate", lambda *args: None)
    def run(command, **kwargs):
        args = command[1:]
        calls.append(args)
        if args[0] == "info":
            kwargs["stdout"].write(b"true\n")
        if args[:2] == ["network", "inspect"]:
            kwargs["stdout"].write(json.dumps([{"internal": mode["network"] == "internal", "driver": "bridge"}]).encode())
        if args[0] == "run" and images["site"]["image"] in args and mode["site"] == "fail":
            return SimpleNamespace(returncode=125)
        for tool, name, payload in (("zap", "zap.json", zap_report()), ("testssl", "testssl.json", tls_report())):
            if args[0] != "run" or images[tool]["image"] not in args:
                continue
            if tool == "zap" and mode["zap"] == "timeout":
                raise subprocess.TimeoutExpired(command, 300)
            volume = Path(args[args.index("-v") + 1].split(":", 1)[0])
            (volume / name).write_text(json.dumps(payload))
            return SimpleNamespace(returncode=2 if tool == "zap" else 0)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(web_tools.subprocess, "run", run)
    return calls, mode


def test_lab_uses_only_internal_network_no_host_ports_and_cleans_up(simulated_runtime):
    calls, _ = simulated_runtime
    result = web_tools.run_lab(authorization_confirmed=True)
    assert result["status"] == "completed"
    assert {item["tool"] for item in result["findings"]} == {"zap", "testssl.sh"}
    create = next(args for args in calls if args[:2] == ["network", "create"])
    assert "--internal" in create
    for args in calls:
        if args[0] == "run":
            assert "--pull=never" in args and "--http-proxy=false" in args
            assert "--cap-drop=all" in args and "--security-opt=no-new-privileges" in args
            assert not {"--privileged", "--publish", "--publish-all"} & set(args)
    tls = next(args for args in calls if "--jsonfile" in args)
    assert "--connect-timeout" in tls and "--disable-rating" in tls
    assert "--socket-timeout" not in tls
    zap = next(args for args in calls if "zap-baseline.py" in args)
    assert "spider.processform=false" in zap[-1] and "spider.postform=false" in zap[-1]
    assert calls[-1][:2] == ["network", "rm"]
    assert len([args for args in calls if args[:2] == ["rm", "--force"]]) >= 3
    assert result["finished_at"] and "synthetic-private-value" not in json.dumps(result)


def test_scanner_timeout_keeps_partial_result_and_removes_containers(simulated_runtime):
    calls, mode = simulated_runtime
    mode["zap"] = "timeout"
    result = web_tools.run_lab(authorization_confirmed=True)
    assert result["status"] == "partial"
    assert result["checks"][0]["status"] == "failed"
    assert "timeout" in result["checks"][0]["error"]
    assert result["checks"][1]["status"] == "completed"
    assert calls[-1][:2] == ["network", "rm"]


def test_failed_site_start_still_cleans_created_resources(simulated_runtime):
    calls, mode = simulated_runtime
    mode["site"] = "fail"
    with pytest.raises(WebError, match="start"):
        web_tools.run_lab(authorization_confirmed=True)
    assert calls[-1][:2] == ["network", "rm"]


def test_non_internal_network_blocks_execution_before_starting_site(simulated_runtime):
    calls, mode = simulated_runtime
    mode["network"] = "external"
    with pytest.raises(WebError, match="not isolated"):
        web_tools.run_lab(authorization_confirmed=True)
    assert not any(args[0] == "run" for args in calls)
    assert calls[-1][:2] == ["network", "rm"]


def test_symlink_report_is_rejected(tmp_path):
    target = tmp_path / "outside.json"
    target.write_text("[]")
    link = tmp_path / "report.json"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="regular file"):
        web_tools.read_report(link)


def test_lab_cli_prints_json_without_loading_repository_credentials(monkeypatch, capsys):
    from cybercheck.__main__ import main
    monkeypatch.setattr(sys, "argv", ["cybercheck", "web-lab", "--authorization-confirmed", "--profile", "fixed"])
    monkeypatch.setattr("cybercheck.__main__.load_dotenv", lambda: pytest.fail("Must not load credentials"))
    def scan(*, authorization_confirmed, profile, progress):
        assert authorization_confirmed and profile == "fixed"
        return {"kind": "web-lab", "status": "completed", "profile": profile}
    monkeypatch.setattr(web_tools, "run_lab", scan)
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0 and json.loads(capsys.readouterr().out)["profile"] == "fixed"


def test_lab_cli_rejects_arbitrary_target_before_runtime(monkeypatch):
    from cybercheck.__main__ import main
    monkeypatch.setattr(sys, "argv", ["cybercheck", "web-lab", "https://outside.example/", "--authorization-confirmed"])
    monkeypatch.setattr(web_tools, "run_lab", lambda **kw: pytest.fail("An arbitrary URL must not reach the runtime"))
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
