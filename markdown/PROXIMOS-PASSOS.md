# CyberCheck next steps

Before taking a task, read the [developer and LLM guide](IMPLEMENTACAO.md) for English-language requirements, code and security standards, verification, and handoff rules. Confirm your workstream and file ownership in [FRENTES-DE-TRABALHO.md](FRENTES-DE-TRABALHO.md), then select an agreed item below. Keep this file as the task checklist; maintain implementation standards in the guide.

Status updated on November 17, 2026. The initial foundation exists and the real GitHub flow has been validated. The complete MVP is not ready yet. Public hosting and the AI provider/model remain deferred; another team member will implement the demo UI.

## Workstream summary

Repository-security changes add required PR tests/security checks, CodeQL, a default-branch Scorecard workflow, Dependabot configuration, and a versioned `main` ruleset. See the [repository-security guide](IMPLEMENTACAO.md#repository-security-and-merge-checks). These workflows protect CyberCheck's source; automatic analysis of customers' projects remains deferred. When changing a required job name, coordinate the corresponding GitHub ruleset update.

| Workstream | Completed | Remaining |
| --- | --- | --- |
| 1. Backend and data | FastAPI API, local Bearer token, SQLite, queue, history, and deletion | Stabilize frontend schemas, expand concurrency validation, and implement per-user authorization |
| 2. Analysis and worker | Three scanner adapters, worker, normalization, initial limits, and temporary cleanup | Expand coverage and dependency formats, calibrate false positives, and complete isolation/resource limits |
| 3. GitHub and maintenance | Organization App installed read-only, selected repository, real commit resolution and download validated | Test private access/revocation, collect discontinuation/archival signals, and evaluate alternatives |
| 4. Demo UI | Existing presentation website; operational UI not started | Build screens and integrate the real API, including partial states, history, and deletion |

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

- [ ] Define stable response and error schemas with workstream 4.
- [ ] Complete OpenAPI documentation and integration examples.
- [ ] Expand concurrency, persistence, and deletion tests.
- [ ] Define per-user login and authorization with workstream 3; the current foundation is single-operator.
- [ ] Integrate templates/static files when delivered by workstream 4.

**Done when:** the contract supports the UI and data access follows the user model actually implemented.

## Workstream 2 — Next tasks

- [ ] Validate all planned categories with vulnerable, corrected, and false-positive cases.
- [ ] Document covered dependency formats and versions; add examples with resolved versions.
- [ ] Expand invalid-output, network-failure, interruption, and resource-cleanup tests.
- [ ] Complete isolation and resource limits. Separate processes, timeouts, and size limits are not a complete sandbox.
- [ ] Integrate maintenance signals supplied by workstream 3.

**Done when:** coverage and limits are demonstrated, and issues include evidence, priorities, and appropriate uncertainty.

## Workstream 3 — Next tasks

- [ ] Test an authorized private repository we own, pagination, and installation revocation.
- [ ] Support per-user login/authorization without editing workstream 1 files concurrently.
- [ ] Associate each dependency with the correct repository and official channels.
- [ ] Collect explicit maintainer notices and archival status, with sources and dates.
- [ ] Check successors and repository moves before recommending replacements.
- [ ] Evaluate alternatives for suitability, maintenance, license, and migration effort; state when no verified candidate exists.

**Done when:** access is authorized and maintenance signals have verifiable evidence. Inactivity alone must not trigger an abandonment diagnosis.

## Workstream 4 — Next tasks

- [ ] Repository selection, authorization confirmation, and manual start.
- [ ] Execution progress and messages for failures/checks not performed.
- [ ] Findings by type and priority, with evidence, confidence, and suggested actions, without scores.
- [ ] Commit and timestamp display.
- [ ] History and deletion with confirmation.
- [ ] Desktop/mobile review and real API integration.

**Done when:** users can complete the flow without simulated data being presented as real results. Do not embed real credentials in the frontend.

## Deferred decisions and delivery

- AI provider/model, costs, and authorization to send the minimum required data.
- Publication and judge access through a link, to be resolved before submission according to the rules.
- Video, links, and final review of event requirements.
- Python version matrix validation: declared 3.11+, tested so far on 3.14.10 on Linux.
- Dependency notices/licenses and a reproducible Python installation strategy.
- TestClient/httpx deprecation warning: non-blocking for current tests, but should be tracked.

Continuous monitoring, external analysis, GitHub Actions or other automatic triggers, and commercial plans remain outside this first delivery.

## References

- [Proposal and decisions](PROJETO.md)
- [Implementation guide](IMPLEMENTACAO.md)
- [GitHub setup and tests](GITHUB.md)
- [Workstream ownership](FRENTES-DE-TRABALHO.md)
- [Event submission draft](RASCUNHO.md)
- [Consulted event rules](regulamento-atual.md)
