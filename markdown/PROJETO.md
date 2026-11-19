# CyberCheck

Living proposal document. Updated on November 17, 2026. The scope below describes the intended product; the actual implementation status is reported separately.

Update on November 18, 2026: the user prioritized external website assessment before returning to repository-analysis work. The first delivery was a terminal command; the user subsequently authorized queued API integration and a frontend contract. Basic checks for TLS, response security headers, and cookie attributes are now available through `cybercheck web URL --authorization-confirmed` or the API, with shared queue/history/report/deletion support. See the [usage and limits](../README.md#analyze-an-authorized-website) and [frontend contract](API.md). This mode does not crawl, authenticate, inject payloads, or prove exploitability. ZAP/testssl.sh remain limited to the isolated CLI laboratory. The repository-analysis implementation remains available.

## Proposal

CyberCheck helps independent developers and small teams identify potential security issues in their projects and understand what to fix first.

The first version will focus on internal repository analysis. Reports bring together findings, evidence, locations, potential impact, and prioritized remediation actions.

The product can support different types of software, beyond web applications. Actual coverage depends on the languages, tools, and checks implemented.

## Implementation status on November 17, 2026

A FastAPI backend already exists, with single-operator token authentication, a SQLite queue and history, a separate worker, and adapters for all three scanners. Another team member will build the operational demo interface, which has not been implemented yet.

The organization's GitHub App is installed with read-only Contents and Metadata permissions, limited to the selected repository. Real access, commit resolution, download, API requests, queue processing, and report retrieval have been validated. The temporary copy was discarded, and the report records the SHA and timestamps.

Bandit 1.9.4, OSV-Scanner 2.7.1, and Betterleaks 1.10.1 have been run against controlled examples. In the real analysis of the `pedro` branch, Bandit and Betterleaks completed; dependencies were not assessed because that revision contained no supported file. The result was explicitly partial. The current suite passed with 24 tests.

Remaining work includes user login and authorization, real tests with a private repository and revoked access, broader coverage validation, stronger worker isolation, collection of discontinuation/archive signals, evaluation of replacements, and the interface. External AI and hosting remain deferred.

Details and responsibilities: [workstreams](FRENTES-DE-TRABALHO.md), [next steps](PROXIMOS-PASSOS.md), and [GitHub configuration](GITHUB.md).

## Decisions made

- Initial audience: independent developers and small teams.
- Initial mode: internal repository analysis.
- First language analyzed in the MVP: Python.
- Initial project input: GitHub integration.
- Integration through a GitHub App, supporting public and private repositories, with read access limited to repositories selected by the user.
- Code is obtained as a temporary copy for analysis and deleted afterward; retain the report with necessary evidence and masked secrets.
- Each analysis must record the repository, the full SHA of the commit actually analyzed, and the analysis timestamp, displayed in the report.
- MVP trigger: manual, with the user selecting a repository and clicking “Start analysis.” Future options remain open for GitHub Actions or other automation, such as GitHub events, CI/CD pipelines, or schedules. No future mechanism has been selected or included in the MVP.
- Focus: security issues with suggested actions.
- Confirmed MVP areas: code, dependencies, and secrets/configuration.
- External website analysis: basic transport, header, and cookie checks are available through the terminal and queued API. Authenticated and active vulnerability testing remain outside this increment; the frontend is developed by another team member against the published contract.
- Monitoring for new risks: future development.
- Commercial plans and billing: decide later.

## Confirmed MVP analysis areas

The MVP will include the three areas below. Specific rules and checks remain to be chosen; approval of these areas does not imply complete coverage of every category.

| Category | Examples |
| --- | --- |
| Potentially vulnerable code | SQL injection, shell command injection, and other unsafe patterns |
| Dependencies | Versions affected by known vulnerabilities |
| Secrets and configuration | Potentially exposed passwords, tokens, and keys; unsafe configuration in the repository |

Each finding must distinguish observations, suspicions, and confirmed issues. The absence of alerts does not guarantee security. A URL such as `/admin`, by itself, does not prove a vulnerability.

### Confirmed initial Python code coverage

- Potential SQL injection.
- Potential shell command injection.
- Dangerous use of `eval` and `exec` with external input.
- Unsafe deserialization of untrusted data.

Checks must consider data origin and usage context. The presence of a function alone does not confirm a vulnerability. The initial tool is Bandit; specific rules and detection limits still require validation.

### Confirmed initial dependency coverage

- Identify libraries and versions used, indicating where they were found.
- Query known vulnerabilities and show the issue, severity, and fixed version when available.
- Assess signs of dependency abandonment or discontinuation.
- Suggest possible replacements when a dependency is abandoned, discontinued, or has no viable fix.

An affected version does not prove that the issue is exploitable in that project. Likewise, time without releases or commits alone does not prove abandonment: a library may be stable.

In the MVP, maintenance assessment is limited to two signals: an explicit maintainer notice of abandonment/discontinuation or an archived upstream repository. Record the source, consultation date, and evidence. Do not use time since commits/releases, activity frequency, or lack of responses as criteria at this stage. Present the observed fact: an archived repository may have a successor or a new location, so do not assert definitive abandonment without context. The absence of these signals does not prove active maintenance. Collection mechanisms and criteria for selecting alternatives remain to be defined.

Alternatives must be checked for maintenance, suitability for the project's use case, license, and migration effort. Explain why each candidate may fit, relevant differences, and uncertainties. Do not promise automatic replacement or drop-in compatibility; report when no suitable alternative has been identified.

### Confirmed initial secrets and configuration coverage

- Potentially exposed repository credentials, such as passwords, tokens, and keys.
- Debug mode enabled in configuration potentially intended for production.
- Disabled TLS certificate validation.

Consider context: fictional examples, development configuration, and tests must not automatically be treated as actual production exposure. Show evidence and uncertainties, mask secrets in results, and do not test credentials against external services. Specific rules and covered frameworks remain to be defined.

## Proposed experience

1. The developer authorizes the GitHub App for selected repositories and chooses one for analysis. The MVP will support public and private repositories with the necessary read permissions. Read-only Contents and Metadata permissions have already been configured in the organization's installation. The current code uses a single operator; individual login and authorization remain to be implemented.
2. The developer clicks “Start analysis”; the system identifies technologies and runs the available checks.
3. The result presents findings with evidence and suggested actions.
4. The developer applies fixes and can run another analysis to compare results.

This flow guides the product; implementation details are still being defined.

### Analysis history

Results must be linked to the exact code revision: repository, full commit SHA, and analysis timestamp. The report represents that revision at that time, without assuming it describes the project's current state. Record timestamps with an explicit time zone.

The code copy is temporary and must be discarded when execution ends, including on failure. The report may contain necessary evidence snippets with secrets masked. Reports and their metadata remain in history until the user deletes them. Users must be able to delete their own reports and associated evidence. The concrete deletion flow remains to be defined.

## Tools selected for the MVP

- **Bandit (Apache-2.0):** unsafe Python code patterns and some configuration checks.
- **OSV-Scanner (Apache-2.0):** known vulnerabilities in dependencies identified in supported files, preferring resolved versions.
- **Betterleaks (MIT):** potentially exposed credentials and secrets.

Selection confirmed by the user. Versions, rules, configuration, and practical coverage still require validation. The MVP's abandonment assessment will use explicit maintainer notices and upstream repository archival. Collecting this evidence and suggesting replacements still require technical definition. OpenSSF Scorecard is not necessary for these two signals and remains a reference for possible future development, without confirmed adoption.

## Presenting results

Expose the issues found, grouped by type and organized by priority. Do not assign an overall grade, category score, or security score to the project.

Each finding presents evidence, a location when applicable, potential impact, and a suggested action, linked to the commit and analysis timestamp. Distinguish confidence from priority: a high-impact suspicion remains a suspicion.

Priorities will be critical, high, medium, and low, considering tool-reported severity and available context, always with a rationale for each finding. When information is insufficient to classify a finding, show “priority to review.” Confidence remains separate from priority. Final category names and detailed classification rules remain to be defined. The Scorecard reference inspires the organization of checks, rather than a scoring system.

## Confirmed MVP stack

- Python backend with FastAPI.
- HTML/CSS interface and Jinja2 templates, with little JavaScript.
- SQLite persistence for users, projects, analyses, and findings.
- A separate Python process to run Bandit, OSV-Scanner, and Betterleaks without blocking website requests.

The priority is to implement the program. Decision updated on November 17, 2026: run the demo locally on the presentation computer. Public hosting, AWS, and other providers are outside this stage's scope. Worker isolation and analysis coordination must be addressed during implementation. A separate process does not itself provide security isolation. SQLite requires persistent storage in the chosen environment.

Before submission, define how the demo will be made available under rules 7.2 and 7.3. Local execution is confirmed; judge access through a link remains a submission requirement to resolve, without blocking implementation.

## AI's role in the MVP

Specialized tools generate findings; AI helps explain them, add context, and suggest fixes based on evidence. AI will neither be solely responsible for detection nor automatically confirm vulnerabilities.

Send AI the structured finding and only the minimum necessary code snippet, with secrets masked, rather than the entire repository. Content extracted from the project remains untrusted data, even in a structured format.

AI will produce explanations and suggestions without GitHub access or permission to execute commands or modify files. Suggestions must remain linked to evidence and state uncertainties.

User decision: leave the AI provider and model open for now, including while hackathon benefits are evaluated. This choice must not block implementation of analysis and evidence presentation. Until the integration is configured and authorized, do not send data to external AI or present explanations as AI-generated. Costs and data handling remain to be defined. Before using an external service, tell the user which data will be sent and establish the corresponding authorization; GitHub integration does not itself authorize this sharing.

## Future development: monitoring

Track new security advisories, compare them with project inventories, and reassess potential exposure. Notify responsible parties with evidence, urgency, and remediation guidance, explicitly stating when exposure has not yet been confirmed.

Sources, frequency, contact channels, and commercial plans remain open.

## Research for choosing languages

Research conducted on November 15, 2026. The priority is to select languages relevant to the audience, without confusing the language analyzed with the language used to build CyberCheck.

### Developer-reported usage

The Stack Overflow Developer Survey 2026 reports the following language-question results, with 14,099 respondents:

| Language | Reported usage |
| --- | ---: |
| JavaScript | 62.0% |
| Python | 58.0% |
| TypeScript | 43.8% |
| Java | 27.6% |
| C# | 27.1% |
| C++ | 24.3% |
| C | 21.8% |
| PHP | 17.7% |
| Go | 16.5% |

The question allows multiple answers: percentages are not mutually exclusive market shares and must not be added together. This table selects candidate languages; it does not reproduce the full ranking, which also includes SQL, HTML/CSS, and shells.

Source: [Stack Exchange Inc., Stack Overflow Developer Survey 2026 — languages](https://survey.stackoverflow.co/2026/technology/data/languages), data under ODbL 1.0. The [methodology](https://survey.stackoverflow.co/2026/methodology) describes recruitment through the Stack Overflow community and channels; the sample does not automatically represent all developers.

### GitHub activity

Octoverse 2026 reports that TypeScript, Python, and JavaScript had the largest increases in monthly contributors among the ten leading languages, from September 2025 to September 2026. It also notes that TypeScript had taken the lead by contributors in 2025.

This metric attributes contributors to a repository's primary language and includes different forms of participation. It does not directly measure the number of small projects, potential customers, or demand for security analysis.

Source: [GitHub Octoverse 2026](https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/).

### Interpretation and decision

This research did not identify a directly comparable ranking of languages used specifically in small projects by independent developers or small Brazilian teams. The two sources above are general indicators, rather than measurements of this audience.

**User-confirmed decision:** start by analyzing Python projects in the MVP. JavaScript/TypeScript are candidates for future expansion, without an implementation commitment. Starting with Python is a scope decision supported by general indicators, rather than a statistical conclusion that Python leads among small projects.

C and C++ remain options, particularly given the proposer's experience. General data alone does not justify prioritizing them for reach; team familiarity, available tools, and analysis quality must also be considered.

Before promising support, assess actual tool coverage for each language and validate the technologies used by potential users.

## Next decisions, one at a time

1. Implement the program and prepare local demo execution, addressing analysis execution and isolation. Do not provision public hosting at this stage.
2. Define supported Python versions and frameworks.
3. Detail rules and criteria for the three confirmed analysis areas.
4. Revisit the AI provider/model and handling of submitted data later; this decision is deferred and does not block implementation.
5. Define demonstration criteria and the report deletion flow; retention until user deletion is confirmed.

## Documentation references

This document is the reference for the current product idea: independent developers and small teams, internal Python repository analysis through GitHub, and prioritized findings with evidence and suggested actions, without security scores. [RASCUNHO.md](RASCUNHO.md) provides the submission summary, [IMPLEMENTACAO.md](IMPLEMENTACAO.md) guides technical work, and [PROXIMOS-PASSOS.md](PROXIMOS-PASSOS.md) tracks remaining tasks.
