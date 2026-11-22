# CyberCheck MVP readiness

Status snapshot: November 19, 2026. This document describes the remaining work against the agreed product scope, based on the current working tree and the latest recorded checks. It is not a claim that the changes have been committed, merged, deployed, or tested in production.

The implementation backlog remains in [PROXIMOS-PASSOS.md](PROXIMOS-PASSOS.md). Product decisions are in [PROJETO.md](PROJETO.md), integration details in [API.md](API.md), and ownership in [FRENTES-DE-TRABALHO.md](FRENTES-DE-TRABALHO.md). This is a readiness assessment of that scope, not authorization to add every possible security feature.

## 1. What counts as the MVP

The agreed repository MVP lets a developer sign in with GitHub, select a repository accessible to both the user and the GitHub App, confirm authorization, and manually request a Python assessment. A separate worker analyzes the recorded commit and returns findings grouped by category and priority. The developer can understand the evidence and suggested action, retain the report, delete their own report, apply a fix, and request another assessment.

The agreed areas are Python code, dependencies, and secrets/configuration. Dependency maintenance is also in the written scope: explicit discontinuation notices and archived upstream repositories, with evidence and qualified replacement suggestions. An MVP claiming that full scope must implement these capabilities or obtain an explicit scope reduction and update its public description.

Basic website checks are an implemented additional mode. They do not replace the repository flow. External AI, public hosting, active website attacks, and continuous monitoring remain separate decisions.

## 2. What already exists

| Area | Implemented | Evidence and limits |
| --- | --- | --- |
| API | FastAPI, typed responses, input validation, report grouping, history, deletion, CORS, and authentication | Contract 0.3.0 exists. The operational frontend still uses simulated data. |
| Queue and persistence | SQLite queue, transactional migrations, duplicate prevention, capacity limits, worker recovery, and timestamps | Repository and website jobs share the queue. Ownership is enforced on user-facing access and deduplication. |
| GitHub installation access | Read-only App authentication, repository listing, revision resolution, and download | The original organization installation has previous live validation. This does not validate the later user OAuth flow. |
| GitHub user login | PKCE, single-use browser-bound state, encrypted tokens, expiring cookies, CSRF protection, installation selection, and user-token downloads | Implemented and tested with controlled GitHub responses. OAuth is not activated in the current local configuration. |
| Python code analysis | Bandit adapter and 14 selected rules, normalized findings, rule-specific recommendations, and coverage states | Real-tool tests exercise the selected rules, corrected examples, safe controls, and known limitations. This is pattern analysis, not full data-flow analysis. |
| Dependency vulnerability analysis | OSV-Scanner adapter, optional external lookup, normalization, advisory references, and fixed-version evidence | Native tool use has previous controlled-example evidence. A real dependency-bearing repository still needs a documented full product-flow demonstration. |
| Secrets/configuration | Betterleaks adapter, masked findings, disabled credential validation, Flask debug and TLS-verification code checks | Broader positive/negative calibration and real product-flow examples remain necessary. |
| Worker safeguards | Temporary copies, archive checks, size limits, timeouts, output limits, restricted child environment, and cleanup | A separate process and these controls do not provide a complete sandbox. |
| Frontend | Six standalone views in `demo-front/` | Repository selection, progress, findings, filters, and history are simulated and stored in browser memory. |
| Basic website mode | Public HTTP(S) checks through CLI and queued API | Covers selected TLS/header/cookie checks; no crawling, login, or injection testing. |
| Heavier web tools | ZAP/testssl.sh laboratory mode | Limited to an isolated generated laboratory; not an arbitrary-target product integration. |

The latest completed backend suite in this session had **177 passing tests on Python 3.14**, with the existing TestClient/httpx deprecation warning. Bandit, a secret scan of changed/new files, and whitespace checks also passed. This document does not report a new test run. The latest uncommitted changes still need CI on the declared supported versions before integration.

### What the local cronk assessment established

The authorized local assessment inspected 48 tracked files, including six Python files, at commit `3cfd7aafda68979e1a40cfb7c1cd967284fdbd4f`. Bandit and Betterleaks completed with zero findings. OSV was deliberately skipped because external lookup had not been authorized. The result was partial; C code, Git history, ignored files, and untracked files were not assessed by the Python code checks or local snapshot.

That assessment used a one-off orchestration script with the existing adapters. There is currently **no supported local-repository CLI command or API endpoint**. It did not validate GitHub OAuth, the frontend, dependency vulnerability detection, maintenance signals, or the detection of a deliberately vulnerable project.

## 3. Required work for the agreed repository MVP

### MVP-01 — Activate GitHub OAuth

**State:** implemented, configuration incomplete. **Owner:** backend/GitHub workstreams.

Remaining work:

1. Generate the existing GitHub App's Client Secret in its settings and save it locally, never in chat or versioned files.
2. Register or verify `http://127.0.0.1:8000/auth/github/callback` as the callback for the current local deployment.
3. Combine the Client ID, Client Secret, stable session key, and public origin into the active `.env`. A private pending file already contains the retrieved Client ID and generated session key; it is not loaded automatically.
4. Keep API and worker on the same data directory and session key. Restart both together for the owner-aware schema migration.
5. Verify read-only Contents/Metadata permissions and selected repositories. If installs on other users' accounts are needed, configure App installation availability accordingly.

**Done when:** a real browser login identifies the GitHub user through `/auth/me`; the session works after an API restart; logout clears that browser's access; no real token appears in frontend responses or logs. The old operator token must not bypass user mode. Existing operator-owned history must remain private to the operator.

**Current external blocker:** Client Secret missing and browser-control host unavailable in this session. The callback setting has not been verified through the App settings UI. See [GITHUB.md](GITHUB.md#enable-user-login).

### MVP-02 — Connect the operational frontend

**State:** simulation only. **Owner:** DAVI, coordinated with backend.

Remaining work:

1. Replace the simulated adapter boundary in `demo-front/demo-service.js` with real API calls, retaining a clearly separated demo mode only if useful.
2. Add login, current-user identity, logout, expired-session handling, installation selection, and the no-installation/no-repository states.
3. Read `/auth/me`, send cookies with requests, and send `X-CSRF-Token` on POST/DELETE. Use an approved exact origin or a same-origin proxy.
4. Select repositories through the user's installation, handle pagination, and submit the actual repository ID and optional reference.
5. Require explicit ownership/written-permission confirmation and a separate external-dependency-lookup choice.
6. Poll real job states. Do not use a simulated timer to announce that an analysis has finished.
7. Render real reports, evidence, priorities, confidence, tool versions, check failures/skips, coverage limits, full commit SHA, and time-zoned dates.
8. Load persistent history and perform confirmed deletion through the API. Remove example-reset controls from the real-data flow.
9. Handle 401, 403, 404, 409, 422, 429, and safe GitHub/network errors without losing the current page or presenting fake success.
10. Choose and configure the login landing page: the current callback redirects to `/docs`, not to the operational app. Coordinate any redirect change with the frontend rather than accepting arbitrary return URLs.

**Done when:** a user can complete login → installation → repository → authorization → queue → report → history → deletion in the actual browser. Reloading preserves server-stored history. Simulated results are never presented as actual scanner output.

### MVP-03 — Prove real user/repository authorization

**State:** controlled-response tests exist; new live OAuth validation is missing. **Owner:** backend/GitHub workstreams.

Remaining work:

1. Exercise a team-owned public repository and an authorized private repository through user login.
2. Exercise installation and repository pagination with sufficient real data when available. Keep the mocked pagination tests as separate evidence if a large live installation is unavailable.
3. Use two authorized GitHub users with different access. Verify that each sees only permitted repositories and their own reports.
4. Remove repository access or revoke authorization before a queued job downloads its source. Restore permissions afterward when appropriate.
5. Verify expiration/logout behavior and that the worker does not substitute the organization's broader installation token.

**Done when:** unauthorized repository access is refused, another user's report cannot be read or deleted even with its ID, failed jobs retain safe messages, and temporary source is removed. Record which scenarios were live and which remained simulated.

### MVP-04 — Demonstrate all three analysis areas

**State:** adapters exist; complete product-flow evidence is missing. **Owner:** analysis workstream; DAVI supplies the controlled project.

Remaining work:

1. Prepare the separate authorized Python test project already assigned to DAVI, with vulnerable and corrected revisions.
2. Include known unsafe code patterns, a dependency with a known affected resolved version, synthetic secret examples, and insecure configuration examples. Never use working credentials.
3. Document the expected rule/advisory, file, line where applicable, and known misses for each example.
4. Analyze the vulnerable revision through the actual API/worker/frontend flow and save the normalized report with its full SHA.
5. Analyze the corrected revision and verify removal of the targeted findings. Retain unrelated alerts and explicit incomplete checks.
6. Include safe controls and cases requiring review, such as fixed commands without a shell, so the presentation does not equate every alert with an exploitable issue.

**Done when:** one reproducible demonstration shows real findings in code, dependencies, and secrets/configuration, and a second revision removes the intended findings. Zero alerts on cronk alone cannot satisfy this requirement.

### MVP-05 — Establish a dependency coverage contract

**State:** OSV integration exists; supported-input and full-flow evidence need completion. **Owner:** analysis workstream.

Remaining work:

1. Select and document the exact dependency file formats supported in the first delivery, using resolved versions for the demonstration. Do not advertise every format supported upstream without validating the installed adapter/tool combination.
2. Identify the package name, ecosystem, detected version, source file, and whether version resolution is incomplete. The current vulnerability findings do not constitute an inventory of every dependency, especially packages with no advisory match.
3. Run the authorized external lookup on a controlled affected version and a corrected version.
4. Verify advisory IDs/links, severity uncertainty, affected-version matching, and relevant fixed-version information without promising that every listed fix is compatible with the project.
5. Demonstrate unavailable metadata/network failure, unsupported inputs, missing files, and lookup refusal as explicit coverage gaps.
6. Keep input handling static: do not install or execute the analyzed project's dependencies to obtain a result.

**Done when:** users can distinguish a checked dependency from an unknown/unresolved/skipped one, and the supported inputs produce reproducible findings through the product. External lookup only occurs after the existing consent.

### MVP-06 — Implement the agreed maintenance signals

**State:** not implemented. **Owner:** GitHub/maintenance workstream, coordinated with analysis and frontend.

Remaining work:

1. Associate a detected dependency with its actual upstream project using trustworthy package/project metadata. A guessed GitHub name is not sufficient.
2. Collect only the two agreed signals: an explicit maintainer discontinuation notice and upstream repository archival.
3. Store the source URL, observation date, evidence, and uncertainty. Show unavailable evidence honestly.
4. Check for repository moves, successors, and conflicting notices before describing a project as discontinued.
5. Do not use age of the last commit/release or unanswered issues alone as evidence of abandonment.
6. Integrate the observations into persistence, typed report responses, and the operational UI, including any additional external-query disclosure needed.

**Done when:** a controlled example produces a source-backed maintenance observation and a maintained/unknown control is not mislabeled. No observation must not be presented as proof of active maintenance.

**Scope consequence:** this capability is promised in both the proposal and submission draft. Omitting it requires an explicit product-scope decision and updates to those documents; it cannot silently be treated as optional.

### MVP-07 — Provide qualified replacement guidance

**State:** not implemented. **Owner:** maintenance workstream, coordinated with report presentation.

Remaining work:

1. For a demonstrated discontinued/archived dependency or one without a viable fix, investigate a possible successor or replacement.
2. Record why it fits the relevant use case, its maintenance evidence, license, important API/behavior differences, and migration effort.
3. Link the recommendation to verifiable sources and an observation date. Do not claim a drop-in replacement without evidence.
4. Provide an explicit "no verified suitable alternative identified" outcome instead of inventing a candidate.

**Done when:** the demonstrated maintenance case has a justified migration recommendation or an honest unavailable outcome, visible in the report. Automatic code changes and a universal package-replacement engine are not required.

### MVP-08 — Finish actionable report presentation

**State:** structured findings and recommendations exist; real UI integration and completeness need verification. **Owner:** analysis/backend/frontend together.

Remaining work:

1. For each demonstrated finding, explain what was observed, its possible impact, what still needs context review, and the suggested first remediation step.
2. Preserve category, priority, confidence, priority rationale, safe evidence, location where applicable, and tool/advisory identifiers.
3. Review whether existing fields can carry the needed explanation before adding another response field. Coordinate any schema change and UI rendering together.
4. Render completed, partial, failed, skipped, and zero-finding states accurately; a clean-looking page must not hide incomplete coverage.
5. Keep actual secrets and raw scanner output out of stored reports and browser responses.

**Done when:** a developer can explain the issue and next action using the real report, while seeing why it remains a potential issue. No score and no unsupported claim of confirmed exploitation are introduced.

## 4. Reliability and delivery gates

### MVP-09 — Make the local demonstration reproducible

**State:** startup/install commands exist; final integrated rehearsal is missing. **Owner:** backend/integrator.

Remaining work:

1. Document one working startup sequence for API, worker, scanners, and operational frontend, including ports, origins, session key, and database location.
2. Confirm that scanner binaries and versions match the supported adapters and that the demonstration machine has the required dependencies.
3. Document what happens when the worker is stopped, a job is interrupted, an input exceeds limits, or a scanner fails. Demonstrate that partial results remain available.
4. Confirm source/raw-output cleanup on success, failure, and worker recovery; keep reports until the owning user deletes them.
5. Rehearse from a fresh browser session and a documented environment. Include enough setup information for a teammate to repeat the flow.

**Done when:** another teammate can run the agreed demo without relying on this chat, hidden temporary scripts, or credentials committed to Git.

A supported local-repository command would improve developer convenience, but it is not part of the agreed GitHub-based MVP input. If added later, it must define working-tree versus commit semantics, ignored/untracked files, ownership, and report persistence. Do not document the one-off cronk scan as an existing product command.

### MVP-10 — Validate the real UI and its error states

**State:** demo-service tests and prior rendered/DOM-based evidence exist; actual integrated browser validation is missing. **Owner:** DAVI/frontend, with backend support.

Remaining work:

1. Exercise login, selection, consent, polling, filtering, history, deletion, and retry in a real browser.
2. Check desktop and mobile layouts, keyboard navigation, visible focus, input labels, status announcements, and confirmation dialogs.
3. Exercise empty lists, no authorized installation, expired session, unavailable GitHub, queue full, running-job deletion refusal, and partial/no-finding reports.
4. Verify session isolation when switching accounts and ensure the UI does not retain another user's data after logout.

**Done when:** the integrated app completes its primary flow and failure recovery on the presentation machine with recorded observations. Existing mock-service tests alone do not close this gate.

### MVP-11 — Integrate and verify the current working changes

**State:** multiple implementation/documentation changes are uncommitted. **Owner:** integrator.

Remaining work:

1. Review the complete diff, including new authentication code/tests and the earlier scanner changes. Split commits by coherent purpose when committing is authorized.
2. Keep `.env`, private keys, session keys, local reports, and `.data/` out of the commits. Check candidate/staged content for secrets.
3. Run the appropriate automated suite and required security checks after integration. Verify Python 3.11 and 3.14 through the configured CI; the latest local result only establishes Python 3.14 execution.
4. Fix documentation/setup links that still refer to the previous `static/demo/` path; the actual operational frontend is in `demo-front/`.
5. Review dependency/tool/font notices and document a repeatable Python dependency setup for the demo environment. Scanner binaries and web-tool images already have versioned locks; Python dependencies currently use version ranges.
6. Merge through the existing repository checks when publication is authorized. Do not mark local uncommitted work as already delivered to teammates.

**Done when:** teammates can obtain the integrated source, reproduce the application, and see passing required checks for that revision.

### MVP-12 — Separate the local-demo safety boundary from public operation

**State:** initial execution controls exist; full scanner isolation and public-operation hardening remain incomplete. **Owner:** backend/analysis, with deployment responsibility to be assigned.

For the local MVP, restrict demonstration inputs to owned/authorized projects, use synthetic examples, retain the existing limits and cleanup, and disclose the incomplete sandbox. Confirm that analyzed projects cannot execute build/install hooks and that scanner configuration cannot unexpectedly enable external credential validation or data transfer.

Before accepting arbitrary users' repositories or exposing the service publicly, complete and verify CPU/memory/process limits, filesystem isolation from application credentials and other users' jobs, controlled network access for each scanner, and cleanup after enforced termination. Review abuse controls, queue fairness, state/session storage growth, HTTPS/proxy behavior, secret-key management, logs, and persistent storage for that environment.

**Done when for a controlled local demo:** the permitted input boundary and safeguards are documented and demonstrated. **Done when for public operation:** those additional controls are enforced and tested against the chosen deployment. Public multiuser operation is not established by passing OAuth unit tests.

## 5. Conditional or deferred work

| Item | MVP treatment |
| --- | --- |
| AI explanations | Provider/model and data-sharing authorization are deferred by user decision. Static explanations can support the current demo. Do not claim that they are AI-generated. If AI is promised for the submitted deliverable, resolve provider, cost, minimized/masked input, authorization, and failure behavior first. |
| Website UI and live-site validation | Required if the final demonstration advertises the website mode. Basic queued checks exist, but real frontend integration and an authorized deployed-site demonstration remain pending. Preserve URL/DNS/redirect scope protections. |
| ZAP/testssl.sh on arbitrary targets | Separate integration requiring enforced scope for every scanner request. Laboratory availability is not arbitrary-target support. |
| Active web testing, authenticated crawling | Not required for the selected repository MVP; requires a separate policy and authorization decision. |
| C/C++, JavaScript, and other languages | Not supported by the selected Python code rules. The C helper in cronk was not analyzed for code vulnerabilities. |
| Continuous monitoring and automatic GitHub triggers | Deferred. The MVP starts analyses manually. Repository CI protecting CyberCheck is not customer-project monitoring. |
| Automatic patches, PRs, package replacement, or report-diff engine | Not necessary for the current manual assess/fix/reassess flow. |
| Refreshing OAuth tokens automatically | Optional usability improvement. Current sessions intentionally require login again after expiry; the UI must support that behavior. |
| Billing, plans, enterprise controls, multiple workers, and large-scale infrastructure | Outside the currently agreed MVP. |

### Event submission is a separate delivery gate

The repository's recorded event rules and proposal identify demo access, a video, and repository links as submission concerns. Recheck the official event instructions when preparing submission; this document does not certify their current wording or deadlines.

The local demonstration decision does not by itself resolve judge access. Decide how evaluators will access the deliverable, prepare the product video and links, and keep the description consistent with actual features. If an online service is chosen, close the applicable public-operation gates above before publishing. Hosting/provider selection is not silently approved by this checklist.

## 6. Recommended completion order

| Order | Deliverable | Dependencies |
| --- | --- | --- |
| 1 | Activate OAuth and complete one real login (MVP-01) | App secret/callback configuration |
| 2 | Connect real frontend flow (MVP-02) | Active OAuth and contract 0.3.0 |
| 3 | Validate user/private-repository access (MVP-03) | Authorized accounts/repositories |
| 4 | Prepare vulnerable/corrected demonstration and complete dependency evidence (MVP-04/05) | DAVI's project, scanner setup, explicit lookup consent |
| 5 | Complete maintenance observations and qualified alternatives (MVP-06/07) | Verified dependency inventory/upstream mapping |
| 6 | Finish real report explanations and UI validation (MVP-08/10) | Real reports from the previous steps |
| 7 | Rehearse startup, cleanup, recovery, integration, and CI (MVP-09/11/12) | Integrated source and agreed local safety boundary |
| 8 | Prepare evaluator access and submission assets | Final advertised scope; public-operation work if hosting is selected |

These are dependencies and completion criteria, not time estimates or new owner assignments. DAVI's frontend and controlled-project responsibilities are confirmed; other workstream ownership follows the existing coordination document.

## 7. Final acceptance checklist

- [ ] Real GitHub user login and authorized repository selection work in the actual app.
- [ ] The real UI requests and follows a queued assessment of the exact recorded commit.
- [ ] Code, dependency, and secrets/configuration findings are demonstrated with controlled vulnerable/corrected inputs.
- [ ] Dependency inputs, external queries, incomplete coverage, and known misses are documented accurately.
- [ ] The agreed maintenance signals and qualified replacement outcomes are implemented, or an explicit scope change has been approved and reflected everywhere.
- [ ] Findings explain evidence, possible impact, uncertainty, priority, and a practical next action without exposing secrets.
- [ ] History survives reload/restart, ownership is enforced, and confirmed deletion works.
- [ ] Temporary source/raw outputs are cleaned up on success and failure; controlled local operating limits are clear.
- [ ] A teammate can reproduce the integrated demo from documented setup and obtain passing required checks.
- [ ] Submission descriptions and access/video links match what is actually available; any chosen public deployment meets its additional safety gates.

Passing the local scanner test, configuring the GitHub App, or completing the simulated UI individually does not close this checklist. The missing deliverable is the integrated, reproducible user experience with evidence for the scope being claimed.
