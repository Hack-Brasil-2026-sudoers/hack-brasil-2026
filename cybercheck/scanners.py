import json
import os
import re
import signal
import subprocess
import sys
from pathlib import Path

from .config import Settings


PRIORITIES = {"critical": 0, "high": 1, "medium": 2, "low": 3, "review": 4}
BANDIT_RULES = {
    "B102": ("unsafe_execution", "Use of exec", "Avoid executing text as code; use specific operations and validate input."),
    "B201": ("insecure_configuration", "Flask debug mode enabled", "Disable debug mode in production."),
    "B301": ("unsafe_deserialization", "Potentially unsafe object deserialization",
             "Check whether serialized data can be changed by an untrusted party. Avoid pickle and object-restoring "
             "wrappers for untrusted data; prefer plain JSON with schema validation."),
    "B302": ("unsafe_deserialization", "Deserialization with marshal",
             "Do not deserialize untrusted data with marshal. Use a data-only format and validate its structure."),
    "B307": ("unsafe_execution", "Use of eval", "Use a parser for the expected format without executing arbitrary code."),
    "B501": ("insecure_configuration", "Certificate validation disabled", "Enable certificate verification and configure a trusted certificate authority."),
    "B506": ("unsafe_deserialization", "Potentially unsafe YAML loading", "Use a safe loader for the library and validate the input structure."),
    "B602": ("command_injection", "Subprocess started with a shell",
             "Replace shell command construction with an argument list and shell=False. Use a fixed executable "
             "and validate arguments, including options accepted by that executable."),
    "B603": ("command_injection", "Subprocess arguments requiring review",
             "This call does not use a shell. Review control of the executable, arguments, and executable-specific "
             "options. A fixed executable with validated arguments may be acceptable; the call alone does not prove injection."),
    "B604": ("command_injection", "Shell option on a function requiring review",
             "Inspect the called function to confirm what shell=True does. If it invokes a shell, use separate "
             "arguments without shell interpretation and validate untrusted inputs."),
    "B605": ("command_injection", "Process started through a shell",
             "Avoid passing constructed commands to shell-based APIs. Prefer an argument list without a shell, "
             "a fixed executable, and validated arguments."),
    "B606": ("command_injection", "Process execution without a shell requiring review",
             "This API does not inherently invoke a shell. Review control of the executable path and arguments; "
             "a trusted fixed executable with validated arguments may be acceptable."),
    "B607": ("command_injection", "Executable resolved through a partial path",
             "Use the trusted absolute path of the intended executable and review directory permissions. "
             "A partial path can select another executable through the process search path."),
    "B608": ("sql_injection", "Dynamically constructed SQL query",
             "Check whether untrusted values reach the constructed SQL. Bind values with database query parameters. "
             "For dynamic table or column names, use a fixed allowlist; value parameters do not bind identifiers."),
}


class ScannerError(Exception):
    pass


def safe_path(value, source: Path):
    path = Path(value)
    if path.is_absolute():
        path = path.relative_to(source)
    if ".." in path.parts:
        raise ValueError("Finding path is outside the repository")
    return str(path)[:500]


def finding(tool, rule, category, title, path, line, severity, confidence, recommendation, evidence):
    # Omit code and match snippets: raw output may contain undetected secrets.
    priority = severity if severity in PRIORITIES and confidence != "low" else "review"
    return {"tool": tool, "rule_id": rule, "category": category, "title": title,
            "path": path, "line": line, "severity": severity, "priority": priority,
            "confidence": confidence, "status": "potential",
            "priority_reason": (f"Reported severity: {severity}; confidence: {confidence}. "
                                "Exposure in the environment has not been confirmed."),
            "recommendation": recommendation, "evidence": evidence}


def parse_bandit(data, source):
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise ValueError("Invalid Bandit output format")
    results = []
    for row in data["results"]:
        rule = row["test_id"]
        if rule not in BANDIT_RULES:
            continue
        category, title, recommendation = BANDIT_RULES[rule]
        item = finding(
            "bandit", rule, category, title, safe_path(row["filename"], source),
            row.get("line_number"), row["issue_severity"].lower(), row["issue_confidence"].lower(),
            recommendation, {"rule": rule, "cwe": (row.get("issue_cwe") or {}).get("id")},
        )
        item["priority_reason"] += " This pattern-based check does not track data flow or establish input trust."
        results.append(item)
    return results


def parse_betterleaks(data, source):
    if data is None:
        data = []
    if not isinstance(data, list):
        raise ValueError("Invalid Betterleaks 1.x output format")
    results = []
    for row in data:
        # Never store Secret, Match, captures, source lines, or scanner messages.
        rule = row["RuleID"]
        if not re.fullmatch(r"[\w.-]{1,150}", rule):
            raise ValueError("Invalid rule identifier")
        results.append(finding(
            "betterleaks", rule, "exposed_secret", "Potentially exposed credential",
            safe_path(row["File"], source), row.get("StartLine"), "unknown", "unknown",
            "Confirm exposure. If this is a real credential, revoke or rotate it and remove it from the code. "
            "The credential was not tested against its provider.",
            {"rule": rule, "secret": "[REDACTED]", "validated": False},
        ))
    return results


def parse_osv(data, source):
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise ValueError("Invalid OSV-Scanner output format")
    results = []
    for group in data["results"]:
        path = safe_path(group["source"]["path"], source)
        for package in group.get("packages", []):
            info = package["package"]
            for vuln in package.get("vulnerabilities", []):
                severity = str((vuln.get("database_specific") or {}).get("severity", "unknown")).lower()
                if severity not in PRIORITIES:
                    severity = "unknown"
                fixed = sorted({event["fixed"] for affected in vuln.get("affected", [])
                                if affected.get("package", info).get("name") == info["name"]
                                and affected.get("package", info).get("ecosystem") == info["ecosystem"]
                                for span in affected.get("ranges", []) for event in span.get("events", [])
                                if "fixed" in event})
                identity = vuln["id"]
                results.append(finding(
                    "osv-scanner", identity, "vulnerable_dependency", f"Affected dependency: {info['name']}",
                    path, None, severity, "version_match",
                    "Evaluate a compatible fixed version, update the lockfile, and test the project. "
                    "A version match does not establish exploitability.",
                    {"package": info["name"], "version": info["version"], "ecosystem": info["ecosystem"],
                     "advisory": identity, "fixed_versions": fixed,
                     "url": "https://osv.dev/vulnerability/" + identity},
                ))
    return results


def child_limits():
    import resource
    resource.setrlimit(resource.RLIMIT_FSIZE, (16 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def run_command(command, working: Path, timeout):
    env = {"PATH": os.defpath, "HOME": str(working), "TMPDIR": str(working),
           "LANG": "C.UTF-8", "NO_COLOR": "1", "GOMAXPROCS": "2"}
    # Scanners do not inherit tokens, PYTHONPATH, or provider configuration.
    with (working / "stdout").open("wb") as out, (working / "stderr").open("wb") as err:
        try:
            process = subprocess.Popen(command, cwd=working, env=env, stdin=subprocess.DEVNULL,
                                       stdout=out, stderr=err, start_new_session=True,
                                       preexec_fn=child_limits if sys.platform == "linux" else None)
        except FileNotFoundError as exc:
            raise ScannerError("Executable is not installed or its path is incorrect.") from exc
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise ScannerError("Time limit exceeded; check incomplete.") from exc
    return code, (working / "stdout").read_bytes()


def run_scanners(source: Path, working: Path, settings: Settings, dependency_lookup: bool):
    import shutil
    ini = working / "bandit.ini"
    ini.write_text("[bandit]\n")
    empty = working / "empty-ignore"
    empty.write_text("")
    osv_config = working / "osv-scanner.toml"
    osv_config.write_text("")
    def executable(name):
        located = shutil.which(name)
        return str(Path(located).resolve()) if located else name
    bandit_command = [sys.executable, "-m", "bandit", "-r", str(source), "--ini", str(ini),
                      "--ignore-nosec", "-t", ",".join(BANDIT_RULES), "-f", "json", "-q"]
    commands = [
        ("bandit", bandit_command, [sys.executable, "-m", "bandit", "--version"], parse_bandit, {0, 1}),
        ("osv-scanner", [executable(settings.osv_bin), "scan", "source", "-r", str(source),
                         "--format", "json", "--config", str(osv_config), "--no-resolve", "--no-ignore",
                         "--no-call-analysis=go", "--no-call-analysis=rust"],
         [executable(settings.osv_bin), "--version"], parse_osv, {0, 1}),
        ("betterleaks", [executable(settings.betterleaks_bin), "dir",
                         str(source), "--report-format", "json", "--report-path", str(working / "secrets.json"),
                         "--redact", "--no-banner", "--gitleaks-ignore-path", str(empty),
                         "--ignore-gitleaks-allow", "--max-archive-depth", "0", "--max-decode-depth", "0",
                         "--validation=false"],
         [executable(settings.betterleaks_bin), "version"],
         parse_betterleaks, {0, 1}),
    ]
    findings, checks = [], []
    for tool, command, version_command, parser, accepted in commands:
        check = {"tool": tool, "status": "failed", "version": None, "error": None}
        if tool == "osv-scanner" and not dependency_lookup:
            check.update(status="skipped", error="External dependency lookup was not authorized.")
            checks.append(check)
            continue
        try:
            code, version = run_command(version_command, working, 15)
            if code != 0:
                raise ScannerError("Could not identify the tool version.")
            text = version.decode(errors="replace")
            match = re.search(r"\b(?:v)?(\d+\.\d+\.\d+(?:[-+][\w.-]+)?)", text)
            if not match:
                raise ScannerError("Tool version was not recognized.")
            check["version"] = match[1]
            if tool == "betterleaks" and not match[1].startswith("1."):
                raise ScannerError("This adapter requires Betterleaks 1.x.")
            code, raw = run_command(command, working, settings.scanner_timeout)
            if tool == "osv-scanner" and code == 128:
                diagnostic = (working / "stderr").read_text(errors="replace")
                if "No package sources found" in diagnostic:
                    check.update(status="skipped", error="No supported dependency file was found. "
                                 "Provide a lockfile or requirements.txt with resolved versions; "
                                 "dependencies were not assessed.")
                    checks.append(check)
                    continue
            if code not in accepted:
                raise ScannerError("The tool exited with an error; check incomplete.")
            if tool == "betterleaks":
                report = working / "secrets.json"
                raw = report.read_bytes()
            data = json.loads(raw)
            parsed = parser(data, source)
            check["status"] = "completed"
            if tool == "bandit":
                metrics, errors = data["metrics"], data["errors"]
                if not isinstance(metrics, dict) or not isinstance(errors, list):
                    raise ValueError("Invalid Bandit coverage metadata")
                analyzed = set(metrics) - {"_totals"} - {row["filename"] for row in errors}
                if errors:
                    check.update(status="partial" if analyzed else "failed",
                                 error="Some Python files could not be analyzed." if analyzed else
                                 "No Python files could be analyzed.")
                elif not analyzed:
                    check.update(status="skipped", error="No Python files were found within the scanner scope; "
                                 "Python code was not assessed.")
            findings.extend(parsed)
        except ScannerError as exc:
            check["error"] = str(exc)
        except (ValueError, TypeError, KeyError, AttributeError, OSError):
            check["status"] = "failed"
            check["error"] = "Invalid or incomplete output; this tool did not provide a complete assessment."
        checks.append(check)
    findings.sort(key=lambda item: (PRIORITIES[item["priority"]], item["category"], item["path"] or ""))
    return findings, checks
