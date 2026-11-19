# CyberCheck

**Team:** Sudoers · Hack Brasil 2026\
**Track:** Cybersecurity

## Motivation

Independent developers and small teams need to secure their projects without dedicated security specialists. Potentially vulnerable code, outdated dependencies, exposed credentials, and unsafe configuration can introduce risks that are difficult to identify and prioritize.

Technical alerts alone do not always explain what matters or how to start fixing it. Discontinued dependencies can also require migration rather than a simple version upgrade.

## Objective

CyberCheck aims to help developers identify potential security issues and decide what to fix first. The initial focus is internal analysis of Python repositories through GitHub, covering code, dependencies, and secrets/configuration.

Results group findings by type and priority, with evidence and suggested actions, without assigning security scores. Each analysis records the exact commit and timestamp. Dependency maintenance checks and possible alternatives are planned; collection of these signals is not yet implemented.

## Run the project

The initial backend requires Python 3.11+ and Linux. The scanner installer supports Linux x86_64.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python scripts/install_scanners.py
```

Create a local `.env` using `.env.example`, generate a random API token of at least 32 characters, and configure the GitHub App following [GITHUB.md](markdown/GITHUB.md). Set `OSV_SCANNER_BIN` and `BETTERLEAKS_BIN` to the absolute paths of the installed executables in `.tools/`.

Start the API and worker in separate terminals from the repository root:

```bash
.venv/bin/python -m cybercheck api
```

```bash
.venv/bin/python -m cybercheck worker
```

Open `http://127.0.0.1:8000/docs`, select **Authorize**, and enter the local API token. List authorized repositories with `GET /api/repositories`, then request an analysis with `POST /api/analyses`. For example, replace `123` with a returned repository ID:

```json
{
  "repository_id": 123,
  "authorization_confirmed": true,
  "dependency_lookup": false
}
```

Confirm authorization only for projects you own or have written permission to assess. Set `dependency_lookup` to `true` to authorize external dependency metadata queries. Use the returned analysis ID with `GET /api/analyses/{identity}` to check progress and retrieve the report.

The current backend uses a single-operator token. A standalone frontend demo is available with simulated data; real API integration and individual user login remain pending. Keep the backend local. A partial report indicates incomplete coverage; the absence of alerts does not guarantee security.

## Development

The standalone [frontend demo](static/demo/README.md) runs with simulated data and does not need the backend:

```bash
python3 -m http.server 8081 --bind 127.0.0.1 --directory static
```

Open `http://127.0.0.1:8081/demo/`. All six views are available; API integration remains pending. The project presentation website is separate in `website/`.

Run tests with `.venv/bin/python -m pytest -q`. See the [developer and LLM guide](markdown/IMPLEMENTACAO.md), [workstreams](markdown/FRENTES-DE-TRABALHO.md), and [next steps](markdown/PROXIMOS-PASSOS.md). The complete proposal is in [PROJETO.md](markdown/PROJETO.md), and the presentation website is in [website/](website/).
