# CyberCheck

**Team:** Sudoers · Hack Brasil 2026\
**Track:** Cybersecurity

## Motivation

Independent developers and small teams need to secure their projects without dedicated security specialists. Potentially vulnerable code, outdated dependencies, exposed credentials, and unsafe configuration can introduce risks that are difficult to identify and prioritize.

Technical alerts alone do not always explain what matters or how to start fixing it. Discontinued dependencies can also require migration rather than a simple version upgrade.

## Objective

CyberCheck aims to help developers identify potential security issues and decide what to fix first. The initial focus is internal analysis of Python repositories through GitHub, covering code, dependencies, and secrets/configuration.

An additional website mode checks an authorized public page through the terminal or the queued API, starting with transport, response headers, and cookies.

Results group findings by type and priority, with evidence and suggested actions, without assigning security scores. Repository analyses record the exact commit; website analyses record the target URL. Both record timestamps. Dependency maintenance checks and possible alternatives are planned; collection of these signals is not yet implemented.

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

## Analyze an authorized website

The first web mode runs independently of GitHub credentials and the backend. Replace the example URL with a public site you own or have written permission to assess:

```bash
.venv/bin/python -m cybercheck web https://your-authorized-site.example/ --authorization-confirmed
```

The command prints a JSON report with UTC timestamps, observed responses, potential issues, evidence, and suggested actions. Exit codes are `0` for completed checks, `2` for incomplete coverage, and `1` for a failed request/analysis. Invalid input or missing authorization also returns `2`, with an argument error instead of a report. Completion and absence of findings do not guarantee security.

Coverage: certificate verification and negotiated TLS version for HTTPS, unencrypted final HTTP responses, HSTS, CSP presence and `nosniff` on HTML responses, and cookie protection attributes. Findings require context review; there is no security score. Headers are inspected without reading response bodies or retaining raw cookie values.

Only standard HTTP/HTTPS ports and URLs without credentials, queries, or fragments are accepted. Internal/special-use IPs and mixed DNS answers are blocked. Connections use a validated IP while preserving hostname verification. Up to three redirects may stay on the same hostname, with HTTPS downgrades blocked; cookies and credentials are not forwarded. Each connection has a five-second socket timeout; DNS resolution uses the operating system's timeout.

This version does not crawl, log in, submit forms, inject SQL/shell/XSS payloads, enumerate paths, or test all TLS protocols/ciphers. The API provides the same basic checks with persistent history; the operational web-analysis interface is being developed separately.

## ZAP and testssl.sh laboratory

The heavier tools currently run only against a generated local laboratory, using Linux and rootless Podman. Install the official digest-pinned images once:

```bash
.venv/bin/python scripts/install_web_tools.py
```

Then run the tools and view their normalized JSON findings directly in the terminal:

```bash
.venv/bin/python -m cybercheck web-lab --authorization-confirmed
.venv/bin/python -m cybercheck web-lab --authorization-confirmed --profile fixed
```

ZAP performs a depth/child-limited spider and passive analysis; active SQL injection/XSS testing is not enabled. testssl.sh checks TLS protocols, server/certificate defaults, and known TLS weaknesses. Scans may take several minutes; progress goes to stderr and the report to stdout. A warning/failure in tool execution is reported as incomplete coverage, rather than a clean scan.

The runner creates a private internal bridge network, verifies its isolation, and publishes no host ports. Containers have memory/CPU/process limits, no capabilities, and no inherited proxy configuration. The images are pulled beforehand; scans do not have an external network route. There is no arbitrary target URL or production private-address bypass in this command. Raw tool reports and logs exist only in temporary directories and are discarded along with the containers and network after execution.

The `vulnerable` profile deliberately uses weak TLS settings/key strength and missing response protections. `fixed` improves selected headers, cookie attributes, and TLS settings; both use a temporary self-signed certificate, so trust alerts are expected. Neither profile establishes that an application is vulnerability-free. Tool versions, image digests, and licenses are in `web-tools.lock.json`: ZAP uses Apache-2.0 and testssl.sh GPL-2.0. The tools run separately; their source is not copied into CyberCheck.

Both profiles have been exercised with the actual pinned tools. The current testssl.sh image reports an unavailable GOST engine (`engine_problem`); its check therefore remains `partial` even when the process exits with `0`. Remaining alerts, including the laboratory certificate and heuristic application findings, are not suppressed to make the example appear clean.

Tool references: [ZAP Baseline](https://www.zaproxy.org/docs/docker/baseline-scan/) and [testssl.sh](https://github.com/testssl/testssl.sh).

Arbitrary authorized website targets, an egress-enforced scanner proxy, authenticated scans, and active testing remain separate integration work. The existing `web URL` command continues to provide its lightweight public-site checks.

## Development

The standalone [frontend demo](static/demo/README.md) runs with simulated data and does not need the backend:

```bash
python3 -m http.server 8081 --bind 127.0.0.1 --directory static
```

Open `http://127.0.0.1:8081/demo/`. All six views are available; API integration remains pending. The project presentation website is separate in `website/`.

Run tests with `.venv/bin/python -m pytest -q`. See the [developer and LLM guide](markdown/IMPLEMENTACAO.md), [workstreams](markdown/FRENTES-DE-TRABALHO.md), and [next steps](markdown/PROXIMOS-PASSOS.md). The complete proposal is in [PROJETO.md](markdown/PROJETO.md), and the presentation website is in [website/](website/).

Run the website integration tests separately with:

```bash
.venv/bin/python -m pytest tests/test_web_integration.py -q
```

These tests start real HTTP and HTTPS servers bound only to `127.0.0.1` on temporary ports. They serve insecure and corrected pages and verify findings, redirects, cookie redaction, and TLS certificate/hostname checks. Certificates and keys are generated in pytest's temporary directory. Test fixtures alone redirect connections to these servers and trust the temporary CA; production URL validation and internal-address blocking remain unchanged. Servers are stopped automatically, and no external site is contacted. The test environment must permit loopback sockets.

To inspect the example reports, run:

```bash
.venv/bin/python -m pytest tests/test_web_integration.py -k fixed_page -s -q
```

The test prints both JSON reports (`insecure` and `corrected`) in the terminal. `-s` disables pytest's output capture; no report files are written.
