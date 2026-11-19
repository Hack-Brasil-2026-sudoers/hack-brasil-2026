"""Run ZAP and testssl.sh against a self-contained, isolated local laboratory."""
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from .scanners import PRIORITIES, finding
from .store import now
from .web import WebError


ROOT = Path(__file__).resolve().parents[1]
MAX_REPORT_BYTES = 16 * 1024 * 1024


def locked_images():
    data = json.loads((ROOT / "web-tools.lock.json").read_text())
    images = data["images"]
    if set(images) != {"zap", "testssl", "site"}:
        raise WebError("The web tool lockfile is incomplete.")
    for spec in images.values():
        if not re.fullmatch(r"[a-z0-9./_-]+@sha256:[0-9a-f]{64}", spec["image"]):
            raise WebError("Web tool images must be pinned to full digests.")
    return images


def text(value, limit=1200):
    return re.sub(r"<[^>]*>", "", html.unescape(str(value)))[:limit]


def parse_zap(data):
    if not isinstance(data, dict) or not isinstance(data.get("site"), list) or not data["site"]:
        raise ValueError("Invalid ZAP report")
    findings = []
    for site in data["site"]:
        origin = urlsplit(site["@name"])
        if origin.hostname != "lab-site" or origin.port != 8080 or origin.scheme != "http":
            raise ValueError("ZAP report contains an unexpected target")
        for alert in site["alerts"]:
            risk = str(alert["riskcode"])
            severity = {"0": "info", "1": "low", "2": "medium", "3": "high"}[risk]
            if severity == "info":
                continue
            rule = str(alert["pluginid"])
            if not re.fullmatch(r"[0-9]{1,12}", rule):
                raise ValueError("Invalid ZAP rule identifier")
            confidence = {"0": "low", "1": "low", "2": "medium", "3": "high", "4": "high"}[str(alert["confidence"])]
            paths = set()
            for instance in alert.get("instances", []):
                uri = urlsplit(instance["uri"])
                if uri.hostname != "lab-site" or uri.port != 8080 or uri.scheme != "http":
                    raise ValueError("ZAP finding is outside the laboratory")
                paths.add(uri.path[:500] or "/")
            findings.append(finding("zap", rule, "web_security", text(alert["name"], 200), None, None,
                                    severity, confidence, text(alert["solution"]),
                                    {"plugin_id": rule, "paths": sorted(paths), "instance_count": len(alert.get("instances", []))}))
    return findings


def parse_testssl(data):
    if not isinstance(data, list) or not data:
        raise ValueError("Invalid testssl.sh report")
    findings, incomplete = [], []
    for row in data:
        rule, severity = row["id"], row["severity"].lower()
        if not isinstance(rule, str) or not re.fullmatch(r"[\w.-]{1,150}", rule):
            raise ValueError("Invalid TLS check identifier")
        if severity in ("warn", "fatal"):
            incomplete.append(rule)  # Scanner limitations/errors, not confirmed vulnerabilities.
            continue
        if severity in ("ok", "info") or rule.startswith("overall_"):
            continue
        if severity not in ("low", "medium", "high", "critical"):
            raise ValueError("Unrecognized TLS severity")
        recommendation = "Review this TLS check and update the TLS configuration or implementation as appropriate."
        if rule.lower().startswith(("sslv", "tls1", "protocol")):
            recommendation = "Disable obsolete TLS/SSL protocols and retain only versions compatible with the security policy."
        elif rule.startswith("cert"):
            recommendation = "Review certificate trust, key strength, hostname coverage, and expiration; replace the certificate as needed."
        findings.append(finding("testssl.sh", rule, "web_transport", "TLS configuration: " + rule, None, None,
                                severity, "medium", recommendation,
                                {"check": rule, "observation": text(row["finding"], 600)}))
    return findings, incomplete


def read_report(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("Scanner report is not a regular file")
    if path.stat().st_size > MAX_REPORT_BYTES:
        raise ValueError("Scanner report exceeds the size limit")
    return json.loads(path.read_bytes())


def create_certificate(directory, profile):
    # The weak key is a deliberate test stimulus, used only by the generated isolated laboratory.
    key = rsa.generate_private_key(public_exponent=65537, key_size=1024 if profile == "vulnerable" else 2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "lab-site")])
    start = datetime.now(timezone.utc) - timedelta(minutes=1)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(start)
            .not_valid_after(start + timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName("lab-site")]), critical=False)
            .sign(key, hashes.SHA256()))
    (directory / "certificate.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    path = directory / "private.key"
    path.touch(mode=0o600)
    path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                       serialization.NoEncryption()))


def run_lab(*, authorization_confirmed=False, profile="vulnerable", progress=None):
    if not authorization_confirmed:
        raise WebError("Confirm authorization before starting the isolated laboratory.")
    if profile not in ("vulnerable", "fixed"):
        raise WebError("Unknown laboratory profile.")
    runtime = shutil.which("podman")
    if not runtime or sys.platform != "linux" or os.geteuid() == 0:
        raise WebError("The first external-tool laboratory requires Linux and Podman.")
    images = locked_images()
    progress = progress or (lambda message: None)
    identifier = "cybercheck-" + uuid4().hex[:12]
    network, site_name, zap_name, tls_name = (identifier + suffix for suffix in ("-net", "-site", "-zap", "-tls"))
    report = {"kind": "web-lab", "profile": profile, "started_at": now(), "finished_at": None,
              "targets": {"application": "http://lab-site:8080/", "tls": "https://lab-site:8443/"},
              "status": "failed", "findings": [], "checks": [],
              "limitations": ["Only the generated isolated laboratory is supported; no user-supplied URL is accepted.",
                              "ZAP uses a limited spider and passive rules, not active injection tests.",
                              "testssl.sh checks protocols, certificate/server defaults, and known TLS weaknesses.",
                              "The fixture uses a self-signed certificate in both profiles; trust alerts are expected.",
                              "No security score is assigned; raw reports are temporary and discarded."]}
    with tempfile.TemporaryDirectory(prefix="cybercheck-web-lab-") as tmp:
        work = Path(tmp)

        def command(args, *, timeout=30):
            with (work / "command.log").open("wb") as output:
                return subprocess.run([runtime, *args], stdin=subprocess.DEVNULL, stdout=output,
                                      stderr=subprocess.STDOUT, timeout=timeout, check=False).returncode

        def container(name, memory):
            return ["run", "--pull=never", "--name", name, "--network", network, "--http-proxy=false",
                    "--userns=keep-id", "--cap-drop=all", "--security-opt=no-new-privileges",
                    "--memory", memory, "--cpus=1", "--pids-limit=256", "--log-driver=none"]

        if (command(["info", "--format", "{{.Host.Security.Rootless}}"])
                or (work / "command.log").read_text().strip() != "true"):
            raise WebError("The web laboratory requires rootless Podman.")
        for spec in images.values():
            if command(["image", "exists", spec["image"]]) != 0:
                raise WebError("A pinned image is missing. Run scripts/install_web_tools.py first.")
        site_dir = work / "site"
        site_dir.mkdir()
        shutil.copyfile(ROOT / "tests/fixtures/web_lab_site.py", site_dir / "site.py")
        create_certificate(site_dir, profile)
        zap_dir, tls_dir = work / "zap", work / "testssl"
        zap_dir.mkdir()
        tls_dir.mkdir()
        try:
            if command(["network", "create", "--driver=bridge", "--internal", network]) != 0:
                raise WebError("Could not create the isolated laboratory network.")
            if command(["network", "inspect", network]) != 0:
                raise WebError("Could not verify laboratory network isolation.")
            networks = json.loads((work / "command.log").read_bytes())
            if len(networks) != 1 or networks[0].get("internal") is not True or networks[0].get("driver") != "bridge":
                raise WebError("The laboratory network is not isolated; execution blocked.")
            progress("Starting the isolated test website.")
            args = container(site_name, "128m") + ["--detach", "--network-alias", "lab-site", "-v",
                    f"{site_dir}:/site:ro,Z", images["site"]["image"], "python", "/site/site.py", profile]
            if command(args) != 0:
                raise WebError("Could not start the laboratory website.")
            for _ in range(10):
                if command(["exec", site_name, "python", "-c",
                            "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/', timeout=1)"]) == 0:
                    break
                time.sleep(0.5)
            else:
                raise WebError("The laboratory website did not become ready.")
            scans = [
                ("zap", zap_name, zap_dir / "zap.json", container(zap_name, "1g") + ["--env", "JAVA_OPTS=-Xmx512m",
                 "-v", f"{zap_dir}:/zap/wrk:rw,Z", images["zap"]["image"], "zap-baseline.py", "-t", "http://lab-site:8080/",
                 "-m", "1", "-T", "3", "-J", "zap.json", "-s", "-z",
                 "-config spider.maxDepth=2 -config spider.maxChildren=5 -config spider.processform=false -config spider.postform=false"]),
                ("testssl", tls_name, tls_dir / "testssl.json", container(tls_name, "512m") + [
                 "-v", f"{tls_dir}:/reports:rw,Z", images["testssl"]["image"], "--color", "0", "--warnings", "batch",
                 "--connect-timeout", "3", "--openssl-timeout", "3", "--disable-rating", "--protocols", "--server-defaults", "--vulnerable",
                 "--jsonfile", "/reports/testssl.json", "https://lab-site:8443"]),
            ]
            for tool, name, path, args in scans:
                progress(f"Running {tool}; this may take a few minutes.")
                check = {"tool": tool, "version": images[tool]["version"], "image": images[tool]["image"],
                         "status": "failed", "error": None}
                try:
                    code = command(args, timeout=300)
                    check["exit_code"] = code
                    data = read_report(path)
                    if tool == "zap":
                        if code not in (0, 1, 2):
                            raise ValueError("ZAP did not complete")
                        findings = parse_zap(data)
                        partial = False
                    else:
                        if not 0 <= code < 50:
                            raise ValueError("testssl.sh did not complete")
                        findings, partial = parse_testssl(data)
                        check["limitation_checks"] = partial
                        partial = bool(partial) or code != 0
                    report["findings"].extend(findings)
                    check["status"] = "partial" if partial else "completed"
                    if partial:
                        check["error"] = "The tool reported limitations; coverage is incomplete."
                except subprocess.TimeoutExpired:
                    check["error"] = "Scanner timeout; analysis incomplete."
                except (OSError, ValueError, KeyError, TypeError):
                    check["error"] = "Scanner execution or report parsing failed; analysis incomplete."
                finally:
                    command(["rm", "--force", name])
                report["checks"].append(check)
            statuses = [check["status"] for check in report["checks"]]
            report["status"] = "completed" if all(s == "completed" for s in statuses) else (
                "partial" if any(s in ("completed", "partial") for s in statuses) else "failed")
        finally:
            for name in (zap_name, tls_name, site_name):
                command(["rm", "--force", name])
            command(["network", "rm", network])
    report["finished_at"] = now()
    report["findings"].sort(key=lambda item: (PRIORITIES[item["priority"]], item["tool"], item["rule_id"]))
    return report
