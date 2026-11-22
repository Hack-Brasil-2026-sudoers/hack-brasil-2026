import json
from pathlib import Path

import pytest

from cybercheck.config import Settings
from cybercheck.scanners import BANDIT_RULES, ScannerError, run_command, run_scanners


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
            return (0, b"bandit 1.9.4") if "--version" in args else (0, json.dumps({
                "results": [], "errors": [], "metrics": {"sample.py": {"loc": 1}},
            }).encode())
        raise ScannerError("Tool missing in test")

    monkeypatch.setattr("cybercheck.scanners.run_command", command)
    _, checks = run_scanners(source, working, Settings(api_token="x" * 40, osv_bin="test-osv"), True)
    check = next(c for c in checks if c["tool"] == "osv-scanner")
    assert check["status"] == expected
    if expected == "skipped":
        assert "dependencies were not assessed" in check["error"]


@pytest.fixture
def bandit_scan(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    working = tmp_path / "work"
    working.mkdir()

    def command(args, cwd, timeout):
        if "bandit" in args:
            return run_command(args, cwd, timeout)
        raise ScannerError("Other tools are outside this Bandit coverage test")

    monkeypatch.setattr("cybercheck.scanners.run_command", command)

    def scan():
        findings, checks = run_scanners(source, working, Settings(api_token="x" * 40), False)
        return findings, checks[0]

    return source, scan


@pytest.mark.parametrize("rule,category,unsafe,corrected", [
    ("B608", "sql_injection", 'cursor.execute("SELECT * FROM users WHERE name = \'%s\'" % name)',
     'cursor.execute("SELECT * FROM users WHERE name = ?", (name,))'),
    ("B602", "command_injection", 'import subprocess\nsubprocess.run(command, shell=True)',
     'import subprocess\nsubprocess.run(["/usr/bin/printf", "%s", value], shell=False)'),
    ("B307", "unsafe_execution", 'value = eval(text)', 'import json\nvalue = json.loads(text)'),
    ("B102", "unsafe_execution", 'exec(text)', 'value = int(text)'),
    ("B301", "unsafe_deserialization", 'import pickle\nvalue = pickle.loads(data)',
     'import json\nvalue = json.loads(data)'),
    ("B506", "unsafe_deserialization", 'import yaml\nvalue = yaml.load(text)',
     'import yaml\nvalue = yaml.safe_load(text)'),
    ("B201", "insecure_configuration", 'from flask import Flask\napp = Flask(__name__)\napp.run(debug=True)',
     'from flask import Flask\napp = Flask(__name__)\napp.run(debug=False)'),
    ("B501", "insecure_configuration", 'import requests\nrequests.get(url, verify=False)',
     'import requests\nrequests.get(url, verify=True)'),
])
def test_real_bandit_approved_categories_and_corrected_examples(bandit_scan, rule, category, unsafe, corrected):
    source, scan = bandit_scan
    sample = source / "sample.py"
    sample.write_text(unsafe + "  # nosec\n")
    # Repository-supplied suppressions must not control CyberCheck's scan.
    (source / ".bandit").write_text("[bandit]\nexclude = sample.py\nskips = " + rule + "\n")
    findings, check = scan()
    assert check["status"] == "completed" and check["version"]
    issue = next(item for item in findings if item["rule_id"] == rule)
    assert issue["category"] == category and issue["path"] == "sample.py"
    assert issue["line"] > 0 and issue["status"] == "potential"
    assert "code" not in issue["evidence"]
    sample.write_text(corrected + "\n")
    findings, check = scan()
    assert check["status"] == "completed"
    assert not any(item["rule_id"] == rule for item in findings)


@pytest.mark.parametrize("files,expected", [
    ({"README.md": "No Python code"}, "skipped"),
    ({"empty.py": ""}, "completed"),
    ({"broken.py": "def broken(:\n"}, "failed"),
    ({"broken.py": "def broken(:\n", "valid.py": "eval(text)\n"}, "partial"),
])
def test_real_bandit_distinguishes_missing_failed_and_partial_coverage(bandit_scan, files, expected):
    source, scan = bandit_scan
    for name, content in files.items():
        (source / name).write_text(content)
    findings, check = scan()
    assert check["status"] == expected
    if expected != "completed":
        assert check["error"]
    assert bool(findings) is ("valid.py" in files)


def test_real_bandit_fixed_command_remains_a_context_review(bandit_scan):
    source, scan = bandit_scan
    (source / "sample.py").write_text('import subprocess\nsubprocess.run(["/usr/bin/printf", "%s", value])\n')
    findings, check = scan()
    assert check["status"] == "completed"
    issue = next(item for item in findings if item["rule_id"] == "B603")
    assert issue["status"] == "potential"
    assert "has not been confirmed" in issue["priority_reason"]
    assert "does not use a shell" in issue["recommendation"]
    assert "does not track data flow" in issue["priority_reason"]


@pytest.mark.parametrize("rule,code", [
    ("B608", 'cursor.execute(f"SELECT * FROM users WHERE name = \'{name}\'")'),
    ("B608", 'query = "SELECT * FROM users WHERE name = \'{}\'".format(name)'),
    ("B301", 'import pickle as storage\nvalue = storage.loads(data)'),
    ("B301", 'from pickle import load as restore\nvalue = restore(stream)'),
    ("B301", 'import pickle\nvalue = pickle.Unpickler(stream).load()'),
    ("B301", 'import pandas as pd\nvalue = pd.read_pickle(path)'),
    ("B301", 'import jsonpickle\nvalue = jsonpickle.decode(text)'),
    ("B302", 'import marshal\nvalue = marshal.loads(data)'),
    ("B302", 'from marshal import load\nvalue = load(stream)'),
    ("B602", 'from subprocess import Popen as launch\nlaunch(command, shell=True)'),
    ("B604", 'launch(command, shell=True)'),
    ("B605", 'import os\nos.system(command)'),
    ("B606", 'import os\nos.execv(executable, arguments)'),
    ("B607", 'import subprocess\nsubprocess.run(["printf", "%s", value])'),
])
def test_real_bandit_variants_and_deserialization_wrappers(bandit_scan, rule, code):
    source, scan = bandit_scan
    (source / "sample.py").write_text(code + "\n")
    findings, check = scan()
    assert check["status"] == "completed"
    item = next(item for item in findings if item["rule_id"] == rule)
    assert item["category"] == BANDIT_RULES[rule][0]
    assert item["recommendation"] == BANDIT_RULES[rule][2]
    assert item["status"] == "potential"
    if rule == "B301":
        assert "object deserialization" in item["title"]
    if rule == "B604":
        assert "Inspect the called function" in item["recommendation"]
    if rule == "B606":
        assert "does not inherently invoke a shell" in item["recommendation"]
    if rule == "B607":
        assert "absolute path" in item["recommendation"]


def test_real_bandit_safe_controls_do_not_trigger_selected_rules(bandit_scan):
    source, scan = bandit_scan
    (source / "sample.py").write_text('''
import ast
import json
import pickle
import requests
import yaml

value = ast.literal_eval(text)
document = json.loads(text)
settings = yaml.safe_load(text)
other_settings = yaml.load(text, Loader=yaml.SafeLoader)
cursor.execute("SELECT * FROM users WHERE name = ?", (name,))
requests.get(url, verify=True)
example = "eval(text); os.system(command); pickle.loads(data)"
# eval(text) is documentation here, not a call.
''')
    findings, check = scan()
    assert check["status"] == "completed"
    assert findings == []


def test_real_bandit_local_callable_alias_is_a_documented_detection_limit(bandit_scan):
    source, scan = bandit_scan
    (source / "sample.py").write_text("evaluate = eval\nvalue = evaluate(text)\n")
    findings, check = scan()
    assert check["status"] == "completed"
    # Bandit does not resolve assignment aliases; completion is not a clean bill of health.
    assert not any(item["rule_id"] == "B307" for item in findings)


@pytest.mark.parametrize("tool,invalid", [
    ("bandit", {"results": [None]}),
    ("bandit", {"results": [], "metrics": None, "errors": []}),
    ("bandit", {"results": [], "metrics": {"sample.py": {}}, "errors": [None]}),
    ("osv-scanner", {"results": [None]}),
    ("betterleaks", [None]),
])
def test_malformed_output_fails_one_check_without_discarding_other_tools(tmp_path, monkeypatch, tool, invalid):
    source = tmp_path / "source"
    source.mkdir()
    valid = {
        "bandit": {"results": [], "errors": [], "metrics": {"sample.py": {"loc": 1}}},
        "osv-scanner": {"results": []},
        "betterleaks": [],
    }

    def command(args, cwd, timeout):
        current = "bandit" if "bandit" in args else Path(args[0]).name
        if "--version" in args or "version" in args:
            return 0, b"2.7.1" if current == "osv-scanner" else b"1.9.4"
        raw = json.dumps(invalid if current == tool else valid[current]).encode()
        if current == "betterleaks":
            (cwd / "secrets.json").write_bytes(raw)
        return 0, raw

    monkeypatch.setattr("cybercheck.scanners.run_command", command)
    _, checks = run_scanners(source, tmp_path, Settings(api_token="x" * 40), True)
    assert len(checks) == 3
    for check in checks:
        assert check["status"] == ("failed" if check["tool"] == tool else "completed")
