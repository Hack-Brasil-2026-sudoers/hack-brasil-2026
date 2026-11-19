# CyberCheck workstreams

All contributors and coding assistants should first read the [implementation guide](IMPLEMENTACAO.md), including the English-language requirement and shared development standards. Use this document for file ownership and contracts, and [PROXIMOS-PASSOS.md](PROXIMOS-PASSOS.md) for the task checklist.

Organization for the four team members to work in parallel. DAVI (Davi Braz) owns workstream 4: the operational demo interface and a separate deliberately vulnerable Python test website/project for CyberCheck validation, as assigned on November 18, 2026. Owners for the other workstreams remain to be agreed upon. The detailed task checklist is in [PROXIMOS-PASSOS.md](PROXIMOS-PASSOS.md#workstream-4--next-tasks).

Scope update on November 18, 2026: basic website checks are available through the terminal and the queued API. The user authorized integration across workstreams 1 and 2; another member is developing the frontend. Workstream 2 owns `cybercheck/web.py`, `tests/test_web.py`, and `tests/test_web_integration.py`; `cybercheck/__main__.py` exposes the command under workstream 1's shared CLI contract. Web jobs share the worker, history, reports, and deletion routes. The [frontend API contract](API.md) and OpenAPI define the integration; the frontend remains independently owned. Existing repository routes and request fields are preserved.

Workstream 2 also owns the ZAP/testssl.sh laboratory adapter in `cybercheck/web_tools.py`, its tests in `tests/test_web_tools.py`, the isolated site fixture in `tests/fixtures/web_lab_site.py`, `web-tools.lock.json`, and `scripts/install_web_tools.py`. The `web-lab` CLI is coordinated with workstream 1. This first external-tool integration accepts only the generated laboratory, not arbitrary website targets.

After organizing the workstreams, the user resumed work on the GitHub connection and flow validation. The status below was updated on November 17, 2026; each participant should continue only within agreed files and contracts.

## Current status

- An initial API, SQLite store, GitHub App integration, worker, and adapters for the three scanners exist in the working directory.
- The commit containing this document shares the initial foundation with the team. Each workstream should start from that same commit and review contracts before modifying modules.
- All 24 current tests passed on November 17, 2026. The three scanners were also run against controlled examples. The connection and real flow through the selected repository were verified, with a documented partial result; this does not validate the complete product. TestClient emits a deprecation warning about httpx usage, without test failures.
- Frontend update: DAVI has built six standalone demo views in `static/demo/`, using in-memory simulated data only. Real API integration, multiuser login, and discontinuation-signal collection remain pending.
- The team's GitHub App was configured and real access validated on November 17, 2026: authentication, selected repository, commit resolution, temporary download, and API listing. Automated tests still use mocked responses; the queue and report flow was also validated with real code, with dependencies explicitly unassessed due to a missing supported file. An additional private repository and revocation still require real validation.
- The site in `website/` presents the project; it is not the operational demo interface.

## File ownership

Each file should have one responsible workstream. Future directories below are suggested locations; they were not created at this stage.

| Workstream | Responsibility | Exclusively owned files | Suggested branch |
| --- | --- | --- | --- |
| 1. Backend and data | API, CyberCheck authentication, queue, and history | `cybercheck/api.py`, `cybercheck/schemas.py`, `cybercheck/store.py`, `cybercheck/config.py`, `cybercheck/__main__.py`, `tests/test_api.py`, `tests/test_store.py` | `feat/backend` |
| 2. Analysis and executor | Run scanners, normalize findings, and manage execution | `cybercheck/scanners.py`, `cybercheck/worker.py`, `tools.lock.json`, `scripts/install_scanners.py`; new tests in `tests/test_scanners.py` and `tests/test_worker.py` | `feat/analyses` |
| 3. GitHub and dependency maintenance | Repository access and discontinuation/archive evidence | `cybercheck/github.py`; new `cybercheck/maintenance.py`; new tests in `tests/test_github.py` and `tests/test_maintenance.py` | `feat/github` |
| 4. Demo interface — DAVI | Screens, frontend demo data, and future API interaction | `static/demo/`; future `templates/` integration; changes in `website/` only when necessary and agreed | `feat/demo-ui` |

## Workstream 1 — Backend and data

### Done

- API, local Bearer token, input validation, SQLite, queue, history, and deletion route.
- Authentication, duplicate, queue recovery, and deletion tests; real request and report retrieval flow.
- Basic web analysis route, typed response/error schemas, shared web/repository history, CORS `Location` exposure, and [frontend integration examples](API.md).
- Transactional migration preserving existing repository reports; mixed queue limits, concurrent web deduplication, persistence, and deletion tests.

### Remaining

- Validate the published routes, response models, and error contract against workstream 4's actual frontend.
- Expand concurrency validation and connect history/deletion to future per-user authorization; initial operations already have tests.
- Define authentication's evolution: the initial code uses a single-operator token, rather than independent user accounts.
- Ensure authorization evolves accordingly; do not present the current foundation as a ready multiuser service.
- Make minimal changes to serve templates and static files delivered by workstream 4, when needed.

**Deliverable:** tested API and a stable contract for other workstreams, with clear persistence and access rules.

**Do not modify:** scanners, GitHub downloads, or screen styling/implementation.

## Workstream 2 — Analysis and executor

### Done

- Three scanner adapters, installer with hashes, separate worker, and result normalization.
- Timeouts, defensive extraction, temporary cleanup, and representation of partial analyses.
- Three scanners run against controlled examples; Bandit and Betterleaks also run against the real repository.
- Missing dependency sources identified in the real flow and explicitly handled as an unperformed check, with regression tests.

### Remaining

- Review adapters and pin the configuration and versions actually supported.
- Validate vulnerable and fixed examples for approved categories, including false positives.
- Expand the tool/network failure matrix. Tests already cover missing tools, missing dependency sources, timeouts, and recovery of interrupted jobs.
- Expand cleanup and evidence-protection tests; cleanup and partial results have already been observed in the real flow.
- Complete resource limits and necessary executor isolation. A separate process does not provide security isolation.
- Integrate maintenance signals produced by workstream 3 without changing their criteria.

**Deliverable:** a worker that runs checks and returns actual findings and coverage, without executing the analyzed project or testing credentials against providers.

**Do not modify:** endpoints, database schema, login, or screens.

## Workstream 3 — GitHub and dependency maintenance

### Done

- Organization App registered and installed with read-only Contents/Metadata access, limited to the selected repository.
- Protected local configuration; real authentication, listing, SHA resolution, and temporary download validated.
- Integrated API, queue, and worker flow validated without putting credentials or reports in Git. See [GITHUB.md](GITHUB.md).

### Remaining

- Test real access to an authorized private repository owned by the team; the initial installation and selected-repository access already work.
- Expand real pagination and revocation tests. Commit resolution and revision download have already been tested against real GitHub.
- Support workstream 1's user authorization flow without editing the API or configuration in parallel.
- Correctly map each Python package to its upstream project.
- Collect only the two approved signals: explicit maintainer notices and archived repositories, with source and date.
- Check for successors or a new location and suggest alternatives only with evidence of suitability; otherwise report that no alternative was identified.
- Agree with workstream 2 on how to provide the dependency inventory and return this evidence.

**Deliverable:** authorized commit access and verifiable maintenance evidence, without classifying a library as abandoned solely because of inactivity.

**Do not modify:** SQLite schemas, scanner execution, or the interface.

## Workstream 4 — Demo interface

**Owner: DAVI (Davi Braz).** In addition to the interface, DAVI prepares the separate, team-owned test website/project with intentional security flaws and corrected examples. Use fictitious credentials and synthetic data, and coordinate expected coverage with workstream 2 and GitHub access with workstream 3. The test project's location remains to be agreed upon; it must stay separate from CyberCheck's production modules. See [the task checklist](PROXIMOS-PASSOS.md#deliberately-vulnerable-test-websiteproject--davi) for scope and acceptance criteria.

### Frontend preview delivered

`static/demo/` contains the six operational views with a browser hash router, simulated lifecycle, report filters, evidence, history, and deletion/reset confirmation. No backend modules were changed. The demo adapter is the replacement boundary for future integration. Real GitHub/scanner results are not displayed at this stage. See [setup and limitations](../static/demo/README.md).

### Remaining

- Create repository-selection, authorization-confirmation, and manual analysis-start screens.
- Show progress, failures, and incomplete checks.
- Display issues by type and priority, without grades or scores.
- Present evidence, confidence, impact, and suggested actions, as well as commit and timestamp.
- Implement history and deletion with confirmation.
- Validate desktop and mobile use and handle empty states and errors.

**Deliverable:** an interface consuming the real API. While development mocks exist, identify them as simulated data.

**Do not modify:** backend Python, database, authentication, or scanners. Ask workstream 1 for any routes, CORS adjustments, or file-serving configuration. Do not put real tokens, the GitHub App key, or other secrets in HTML/JavaScript or the repository.

## Contracts to agree on before parallel work

### API ↔ interface

Existing initial routes:

| Method and route | Purpose |
| --- | --- |
| `GET /health` | API status |
| `GET /api/repositories` | Repositories accessible to the configured installation |
| `POST /api/analyses` | Request manual analysis of a reference |
| `POST /api/web-analyses` | Queue basic checks for an authorized public website |
| `GET /api/analyses` | Retrieve history |
| `GET /api/analyses/{id}` | Retrieve the report and grouped issues |
| `DELETE /api/analyses/{id}` | Delete an analysis; a running analysis returns a conflict |

The initial request body contains `repository_id`, optional `reference`, `authorization_confirmed`, and `dependency_lookup`. The last option authorizes external dependency metadata queries. Data routes require a Bearer token in the current foundation.

Use [API.md](API.md) and `/openapi.json` for exact requests, typed responses, polling, errors, authentication, and CORS. The additive web request contains `target_url` and a boolean `authorization_confirmed`; its response uses the same analysis envelope and report routes. Workstreams 1 and 4 must coordinate contract changes. Per-user GitHub login does not yet exist: do not build screens assuming this flow is ready.

### Executor ↔ API and database

Initial states: `queued`, `running`, `completed`, `partial`, and `failed`.

The shared analysis has `kind` (`repository` or `web`). Repository reports record identity and SHA; web reports record `target_url` with null repository/revision fields, observed request metadata, and limitations. Both retain timestamps, findings, and check statuses; repository checks also retain tool versions. The `completed` state means configured checks finished, rather than that the project is secure. Scope rules and uncovered cases must be explicit.

Priorities: `critical`, `high`, `medium`, `low`, and `review`. The interface may translate labels while retaining contract values. Confidence and priority are distinct fields.

The initial finding format is in the `finding` function in `cybercheck/scanners.py`. Field changes must be agreed upon by workstreams 1, 2, and 4 before implementation.

### Executor ↔ GitHub

Preserve or explicitly negotiate existing interfaces:

- `repositories(page)`: lists authorized repositories.
- `resolve(repository_id, reference)`: returns full name, SHA, and reference.
- `download(analysis, destination)`: downloads the recorded revision's archive to the specified destination.

Maintenance collection should live in a module separate from the scanner adapter. Workstreams 2 and 3 must agree on its input and output format before integrating this feature.

## Shared files: one responsible integrator

Until the team chooses a person, consider workstream 1 responsible for integrating these files:

- `pyproject.toml`, any future Python lockfile, `.env.example`, and `.gitignore`.
- `README.md`, planning in `markdown/`, and this document.
- `tests/test_backend.py` and `tests/test_security.py`, which already cover multiple workstreams. Workstreams should create new tests in the exclusive files listed in the table, avoiding simultaneous edits to these two.
- Workflows in `.github/` and future repository structure changes.

Anyone needing a dependency or environment variable should notify the integrator rather than editing the shared file in parallel. Do not move files or rename another workstream's functions without agreement.

## Suggested integration order

1. Review and share the current foundation in a common commit; assign owners and confirm contracts.
2. Each participant creates a branch from that base and works within their workstream's files.
3. Workstream 1 stabilizes the API while workstreams 2 and 3 validate their modules; workstream 4 can build screens with clearly identified example data.
4. Integrate changes in small pieces, updating the branch before opening each PR.
5. The integrator runs the test suite and checks the GitHub → queue → analysis → report → deletion flow.

Hosting, AI provider/model, continuous monitoring, GitHub Actions for automatic analysis, and commercial plans do not need to be resolved by these workstreams now.
