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
    "B102": ("unsafe_execution", "Uso de exec", "Evite executar texto como código; use operações específicas e valide a entrada."),
    "B201": ("insecure_configuration", "Depuração Flask habilitada", "Desative debug no ambiente de produção."),
    "B301": ("unsafe_deserialization", "Desserialização com pickle", "Não carregue objetos de origem não confiável; considere JSON com validação."),
    "B302": ("unsafe_deserialization", "Desserialização com marshal", "Não carregue objetos de origem não confiável."),
    "B307": ("unsafe_execution", "Uso de eval", "Use um parser específico para o formato esperado, sem executar código arbitrário."),
    "B501": ("insecure_configuration", "Validação de certificado desativada", "Habilite a verificação do certificado e configure uma autoridade confiável."),
    "B506": ("unsafe_deserialization", "Carregamento potencialmente inseguro de YAML", "Use um carregador seguro adequado à biblioteca e valide a estrutura recebida."),
    "B608": ("sql_injection", "Consulta SQL construída dinamicamente", "Use parâmetros da biblioteca de banco e verifique a origem dos dados."),
}
for _rule in ("B602", "B603", "B604", "B605", "B606", "B607"):
    BANDIT_RULES[_rule] = ("command_injection", "Execução de comando a revisar",
                           "Prefira argumentos separados sem shell, executável fixo e validação das entradas.")


class ScannerError(Exception):
    pass


def safe_path(value, source: Path):
    path = Path(value)
    if path.is_absolute():
        path = path.relative_to(source)
    if ".." in path.parts:
        raise ValueError("Caminho de achado fora do repositório")
    return str(path)[:500]


def finding(tool, rule, category, title, path, line, severity, confidence, recommendation, evidence):
    # Sem trechos de código/match: as saídas cruas podem conter segredos não detectados.
    priority = severity if severity in PRIORITIES and confidence != "low" else "review"
    return {"tool": tool, "rule_id": rule, "category": category, "title": title,
            "path": path, "line": line, "severity": severity, "priority": priority,
            "confidence": confidence, "status": "potential",
            "priority_reason": (f"Gravidade informada: {severity}; confiança: {confidence}. "
                                "Exposição no ambiente ainda não confirmada."),
            "recommendation": recommendation, "evidence": evidence}


def parse_bandit(data, source):
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise ValueError("Formato Bandit inválido")
    results = []
    for row in data["results"]:
        rule = row["test_id"]
        if rule not in BANDIT_RULES:
            continue
        category, title, recommendation = BANDIT_RULES[rule]
        results.append(finding(
            "bandit", rule, category, title, safe_path(row["filename"], source),
            row.get("line_number"), row["issue_severity"].lower(), row["issue_confidence"].lower(),
            recommendation, {"rule": rule, "cwe": (row.get("issue_cwe") or {}).get("id")},
        ))
    return results


def parse_betterleaks(data, source):
    if data is None:
        data = []
    if not isinstance(data, list):
        raise ValueError("Formato Betterleaks 1.x inválido")
    results = []
    for row in data:
        # Nunca guardar Secret, Match, captures, linhas ou mensagens do scanner.
        rule = row["RuleID"]
        if not re.fullmatch(r"[\w.-]{1,150}", rule):
            raise ValueError("Identificador de regra inválido")
        results.append(finding(
            "betterleaks", rule, "exposed_secret", "Possível credencial exposta",
            safe_path(row["File"], source), row.get("StartLine"), "unknown", "unknown",
            "Confirme a exposição. Se for uma credencial real, revogue/rotacione e remova do código. "
            "A credencial não foi testada contra o provedor.",
            {"rule": rule, "secret": "[REDACTED]", "validated": False},
        ))
    return results


def parse_osv(data, source):
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise ValueError("Formato OSV-Scanner inválido")
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
                    "osv-scanner", identity, "vulnerable_dependency", f"Dependência afetada: {info['name']}",
                    path, None, severity, "version_match",
                    "Avalie uma versão corrigida compatível, atualize o lockfile e teste o projeto. "
                    "A associação de versão não comprova explorabilidade.",
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
    # Nenhum token, PYTHONPATH ou configuração de provedor é herdado pelo scanner.
    with (working / "stdout").open("wb") as out, (working / "stderr").open("wb") as err:
        try:
            process = subprocess.Popen(command, cwd=working, env=env, stdin=subprocess.DEVNULL,
                                       stdout=out, stderr=err, start_new_session=True,
                                       preexec_fn=child_limits if sys.platform == "linux" else None)
        except FileNotFoundError as exc:
            raise ScannerError("Executável não instalado ou caminho incorreto.") from exc
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise ScannerError("Tempo limite excedido; verificação incompleta.") from exc
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
            check.update(status="skipped", error="Consulta externa de dependências não autorizada.")
            checks.append(check)
            continue
        try:
            code, version = run_command(version_command, working, 15)
            if code != 0:
                raise ScannerError("Não foi possível identificar a versão da ferramenta.")
            text = version.decode(errors="replace")
            match = re.search(r"\b(?:v)?(\d+\.\d+\.\d+(?:[-+][\w.-]+)?)", text)
            if not match:
                raise ScannerError("Versão da ferramenta não reconhecida.")
            check["version"] = match[1]
            if tool == "betterleaks" and not match[1].startswith("1."):
                raise ScannerError("Este adaptador requer Betterleaks 1.x.")
            code, raw = run_command(command, working, settings.scanner_timeout)
            if code not in accepted:
                raise ScannerError("A ferramenta encerrou com erro; verificação incompleta.")
            if tool == "betterleaks":
                report = working / "secrets.json"
                raw = report.read_bytes()
            data = json.loads(raw)
            findings.extend(parser(data, source))
            check["status"] = "completed"
            if tool == "bandit" and data.get("errors"):
                check.update(status="partial", error="Alguns arquivos Python não puderam ser analisados.")
        except ScannerError as exc:
            check["error"] = str(exc)
        except (ValueError, TypeError, KeyError, OSError):
            check["error"] = "Saída inválida ou incompleta; nenhum diagnóstico completo desta ferramenta."
        checks.append(check)
    findings.sort(key=lambda item: (PRIORITIES[item["priority"]], item["category"], item["path"] or ""))
    return findings, checks
