# hack-brasil-2026

CyberCheck, the Sudoers team's project for Hack Brasil 2026.

CyberCheck helps independent developers and small teams assess Python repositories through GitHub. It presents potential code vulnerabilities, dependency issues, and exposed secrets or unsafe configuration, with evidence and prioritized remediation guidance, without security scores. The current proposal is documented in [PROJETO.md](markdown/PROJETO.md).

## Documentation

- [Submission draft](markdown/RASCUNHO.md)
- [Project proposal and decisions](markdown/PROJETO.md)
- [Developer and LLM guide: workflow, English, and project standards](markdown/IMPLEMENTACAO.md)
- [Next steps](markdown/PROXIMOS-PASSOS.md)
- [Workstreams and file ownership](markdown/FRENTES-DE-TRABALHO.md)
- [GitHub App setup](markdown/GITHUB.md)
- [Event rules — English translation](markdown/regulamento-atual.md)

The project presentation website is in [website/](website/).

## Run the backend

Requires Python 3.11+ and Linux for this initial worker implementation.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python scripts/install_scanners.py
```

Create a `.env` from `.env.example`, generate a random API token, and follow the [GitHub App guide](markdown/GITHUB.md). The scanner installer supports Linux x86_64 and verifies binary hashes.

Start the API and worker in separate terminals from the repository root:

```bash
.venv/bin/python -m cybercheck api
```

```bash
.venv/bin/python -m cybercheck worker
```

Interactive API documentation is available at `http://127.0.0.1:8000/docs`. Select **Authorize**, enter the local token, list repositories, and request an analysis using the returned repository ID. External dependency lookup requires authorization through the `dependency_lookup` field.

```bash
.venv/bin/python -m pytest -q
```

This foundation uses a single-operator token and does not yet provide multiuser isolation. Do not expose the backend as a public service. Partial results indicate missing coverage or failed checks; the absence of alerts does not guarantee security. Another team member will build the operational demo UI.
