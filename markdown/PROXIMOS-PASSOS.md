# CyberCheck next steps

For a detailed snapshot of what still blocks the agreed MVP, including acceptance criteria and conditional/deferred scope, see [MVP-READINESS.md](MVP-READINESS.md). Keep implementation progress in this backlog and refresh that assessment when release scope changes.

Before taking a task, read the [developer and LLM guide](IMPLEMENTACAO.md) for English-language requirements, code and security standards, verification, and handoff rules. Confirm your workstream and file ownership in [FRENTES-DE-TRABALHO.md](FRENTES-DE-TRABALHO.md), then select an agreed item below. Keep this file as the task checklist; maintain implementation standards in the guide.

Implementation baseline updated on November 17, 2026; responsibility assignment updated on November 18, 2026. The initial foundation exists and the real GitHub flow has been validated. The complete MVP is not ready yet. Public hosting and the AI provider/model remain deferred. DAVI is responsible for the demo UI and a deliberately vulnerable test website/project for CyberCheck validation.

## Workstream summary

### Current priority: first website assessment

User decision on November 18, 2026: implement website checks through the terminal before integrating them into the API, then return to repository-analysis work.

- [x] Add an independent `web` command requiring explicit ownership/written-authorization confirmation.
- [x] Check HTTPS certificate verification, negotiated TLS version, HTML security headers, and cookie attributes.
- [x] Return JSON with timestamps, evidence, recommendations, incomplete-check states, and explicit limits, without a score or raw cookie values.
- [x] Block internal/special-use destinations, unsafe URLs, cross-host redirects, and HTTPS downgrades; pin connections to validated public IPs.
- [x] Add focused tests without removing existing tests, including DNS rebinding, redirects, redaction, and TLS/network failures.
- [x] Validate real local HTTP/HTTPS test servers with insecure/corrected pages, redirects, trusted/untrusted certificates, and hostname mismatches. Overrides are restricted to test fixtures; normal local-address blocking remains enabled.
- [ ] Validate a deployed site owned by the team or authorized in writing. Local integration tests do not establish coverage of real hosting environments.
- [x] Integrate basic web checks into the persistent queue, worker, history, report, and deletion flow through `POST /api/web-analyses`; publish typed response models and the [frontend contract](API.md). Jobs execute outside API handlers. Real loopback HTTPS tests cover the complete flow; deployed-site validation and frontend integration remain pending.
- [ ] Decide any later crawling or active testing separately; this delivery sends unauthenticated GET requests only.

### Selected heavier web tools

The user selected ZAP and testssl.sh. Their first integration is the `web-lab` command: ZAP spider/passive checks and testssl.sh TLS checks against a generated laboratory in a verified internal Podman network. This is distinct from the lightweight public-site `web URL` command. No active injection scan or arbitrary external target is enabled.

- [x] Pin official images by digest and keep web tool installation separate from the repository scanners.
- [x] Normalize findings, retain tool versions, omit ZAP raw matches/queries, and report failed or incomplete checks honestly.
- [x] Add tests for parsing, redaction, resource/network settings, failure handling, and cleanup.
- [x] Run ZAP 2.17.0 and testssl.sh 3.2.5 against the actual isolated vulnerable/corrected sites. The corrected profile removes the selected missing-header/cookie and obsolete-protocol/weak-key alerts, but does not eliminate all findings. The testssl.sh image reports `engine_problem` (GOST engine unavailable), so its coverage remains explicitly partial.
- [ ] Extend arbitrary authorized target support only after enforcing egress scope for every scanner request; initial DNS validation alone is insufficient for third-party crawlers.
- [ ] Agree on active-test policies, request limits, and explicit authorization before enabling injection tests.

Commands and current validation limits: [README](../README.md#zap-and-testsslsh-laboratory).

Current API integration verification: 115 automated tests passed on local Python 3.14, with the existing TestClient/httpx deprecation warning. Bandit, `git diff --check`, Markdown file links, and a Betterleaks scan of the candidate files passed. Added tests cover migration, concurrent deduplication, contract compatibility, worker failures, and the real HTTPS end-to-end flow. Native scanner runs are separate evidence from the mocked adapter tests; no real external website was scanned.

Usage and limits: [README](../README.md#analyze-an-authorized-website). Workstream 2 owns `web.py` and its tests; CLI changes are coordinated with workstream 1. The original workstreams remain below.

Repository-security changes add required PR tests/security checks, CodeQL, a default-branch Scorecard workflow, Dependabot configuration, and a versioned `main` ruleset. See the [repository-security guide](IMPLEMENTACAO.md#repository-security-and-merge-checks). These workflows protect CyberCheck's source; automatic analysis of customers' projects remains deferred. When changing a required job name, coordinate the corresponding GitHub ruleset update.

| Workstream | Completed | Remaining |
| --- | --- | --- |
| 1. Backend and data | Typed API contract, operator/GitHub session modes, SQLite, user-scoped shared repository/web queue/history/deletion, migration, and deduplication tests | Activate live OAuth and validate integration with the teammate's frontend |
| 2. Analysis and worker | Three scanner adapters, worker, normalization, initial limits, and temporary cleanup | Expand coverage and dependency formats, calibrate false positives, and complete isolation/resource limits |
| 3. GitHub and maintenance | Organization App installed read-only, selected repository, real commit resolution and download validated | Test private access/revocation, collect discontinuation/archival signals, and evaluate alternatives |
| 4. Demo UI — DAVI | Six standalone frontend views in `static/demo/`, with simulated runs, filters, reports, history, and deletion | Complete real API/authentication integration and real-browser interaction/accessibility validation; build the separate vulnerable test project |

File ownership and contracts are in [FRENTES-DE-TRABALHO.md](FRENTES-DE-TRABALHO.md). Each participant should work within their workstream; shared-file changes go through the integrator.

## Validation evidence

- 24 automated tests passed: authentication, validation, queue, recovery, deletion, archive extraction, normalization, timeouts, environment protection, and checksums.
- Bandit 1.9.4, OSV-Scanner 2.7.1, and Betterleaks 1.10.1 were run against controlled examples.
- The real GitHub App was installed on the organization with read-only Contents/Metadata permissions and explicit repository selection.
- The API → queue → worker → GitHub → scanners → report flow ran against branch `pedro`, commit `156862f5d413c74bd2888f4e45c594883511cc88`.
- Bandit and Betterleaks completed on that revision. OSV found no supported dependency source; the report states that dependencies were not assessed and retains partial status.
- The commit and timestamps were recorded and temporary files discarded. Test history is in `.data/`, outside Git.
- The pre-push check detected no secrets in versionable files or local Git history. The `.env` and private key have permission 600 and are not tracked.

These tests do not guarantee the absence of vulnerabilities or validate every version, environment, or input format.

## Workstream 1 — Next tasks

- [x] Publish typed response/error schemas for workstream 4 in [API.md](API.md); validate against the actual frontend during integration.
- [x] Publish OpenAPI response documentation and integration examples.
- [x] Expand concurrency, persistence, and deletion tests for web jobs and the repository-history migration.
- [ ] Validate the actual frontend against the API and expand operational concurrency testing as deployment needs evolve.
- [x] Implement optional GitHub user login with PKCE, encrypted sessions, CSRF, and owner-scoped history/reports/deletion/deduplication. Keep old reports under the operator and reject operator-token bypass in user mode.
- [ ] Configure OAuth client credentials and callback in the existing App, then validate actual browser login and user-owned repositories. The current machine has only the original installation credentials; mocked tests do not establish live OAuth activation.
- [ ] Integrate templates/static files when delivered by workstream 4.

**Done when:** the contract supports the UI and data access follows the user model actually implemented.

## Workstream 2 — Next tasks

- [x] Validate eight selected Bandit patterns with real vulnerable/corrected examples: SQL construction, shell execution, eval, exec, pickle, YAML loading, Flask debug mode, and TLS verification. Assert repository suppression bypass, distinguish absent/failed/partial Python coverage, and preserve other tools' findings when one scanner returns malformed output. A fixed executable without a shell still produces B603; retain it as a potential issue requiring context. This does not complete dependency/secret coverage calibration.
- [x] Extend real-tool validation to all 14 selected Bandit rules, including marshal, pandas/jsonpickle wrappers, import aliases, SQL formatting variants, shell wrappers, and partial executable paths. Verify safe controls and distinguish rule-specific command recommendations. Persist explicit code-analysis limits in repository reports and demonstrate the missed assignment-alias eval case. General framework and data-flow analysis remain outside the demonstrated coverage.
- [ ] Validate all planned categories with vulnerable, corrected, and false-positive cases.
- [ ] Document covered dependency formats and versions; add examples with resolved versions.
- [ ] Expand invalid-output, network-failure, interruption, and resource-cleanup tests.
- [ ] Complete isolation and resource limits. Separate processes, timeouts, and size limits are not a complete sandbox.
- [ ] Integrate maintenance signals supplied by workstream 3.

**Done when:** coverage and limits are demonstrated, and issues include evidence, priorities, and appropriate uncertainty.

## Workstream 3 — Next tasks

- [ ] Test an authorized private repository we own, pagination, and installation revocation.
- [x] Integrate user authorization with workstream 1: list user-accessible installations/repositories, resolve revisions and download as the user, recheck access in the worker, and fail closed on logout/expiry/revocation without installation-token fallback. Controlled GitHub-response tests cover these scenarios; real access tests remain pending.
- [ ] Associate each dependency with the correct repository and official channels.
- [ ] Collect explicit maintainer notices and archival status, with sources and dates.
- [ ] Check successors and repository moves before recommending replacements.
- [ ] Evaluate alternatives for suitability, maintenance, license, and migration effort; state when no verified candidate exists.

**Done when:** access is authorized and maintenance signals have verifiable evidence. Inactivity alone must not trigger an abandonment diagnosis.

## Workstream 4 — Next tasks

**Owner: DAVI (Davi Braz).** Current responsibilities: build the operational demo website and prepare a separate website/project with intentional cybersecurity flaws for testing CyberCheck. The existing `website/` directory remains the presentation site. Frontend-first implementation is confirmed: `static/demo/` uses demonstration data only; connect the real backend after its contract is ready.

### Operational demo website — DAVI

- [x] Frontend repository selection, authorization confirmation, and manual simulated start.
- [x] Simulated execution progress and examples of failures/checks not performed.
- [x] Demonstration findings by type and priority, with evidence, confidence, and suggested actions, without scores.
- [x] Example full commit SHA and explicitly time-zoned timestamp display.
- [x] In-memory demo history and deletion/reset with confirmation.
- [ ] Complete real-browser interaction and accessibility validation in addition to rendered desktop/mobile captures and DOM-emulated checks.
- [ ] Agree the final response/error/authentication contract with workstream 1, then replace the demo adapter with real API integration.

Frontend evidence: seven Node.js demo-service tests passed. A separate DOM-emulated workflow pass covered selection, authorization, simulation, filtering, reports, deletion, reset, and recovery. Impeccable captures were produced at desktop and mobile sizes; browser-driven control and assistive-technology testing remain pending. See [frontend setup](../static/demo/README.md).

**Done when:** users can complete the flow without simulated data being presented as real results. Do not embed real credentials in the frontend.

### Deliberately vulnerable test website/project — DAVI

- [ ] Prepare a separate, team-owned Python web project with intentional security flaws within CyberCheck's approved analysis categories.
- [ ] Include controlled examples of unsafe code, vulnerable dependency versions, and secrets/insecure configuration. Use fictitious credentials and synthetic data only.
- [ ] Document each intentional flaw, its location, and the expected scanner finding or known coverage limitation; coordinate expectations with workstream 2.
- [ ] Provide corrected counterparts or revisions to demonstrate findings before and after fixes, recording the commit analyzed.
- [ ] Make the test repository available to the authorized GitHub App for the existing repository-analysis flow, coordinating access with workstream 3.

**Done when:** the project provides reproducible inputs for real CyberCheck analyses, with expected and observed results documented, including missed detections and false positives. This is a controlled local test project; public deployment is outside this task. CyberCheck reads its repository without running the vulnerable application. Scanning a live website URL remains outside the MVP.

## Deferred decisions and delivery

- AI provider/model, costs, and authorization to send the minimum required data.
- Publication and judge access through a link, to be resolved before submission according to the rules.
- Video, links, and final review of event requirements.
- Python compatibility: declared 3.11+; existing CI passed on Python 3.11 and 3.14. Revalidate new changes through CI as well as local Python 3.14 tests.
- Dependency notices/licenses and a reproducible Python installation strategy.
- TestClient/httpx deprecation warning: non-blocking for current tests, but should be tracked.

Continuous monitoring, authenticated/active web testing, automatic product scan triggers, and commercial plans remain deferred. The first external web CLI is now included as described above; repository CI workflows do not implement automatic customer-project scans.

## References

- [Proposal and decisions](PROJETO.md)
- [Implementation guide](IMPLEMENTACAO.md)
- [GitHub setup and tests](GITHUB.md)
- [Workstream ownership](FRENTES-DE-TRABALHO.md)
- [Event submission draft](RASCUNHO.md)
- [Consulted event rules](regulamento-atual.md)
