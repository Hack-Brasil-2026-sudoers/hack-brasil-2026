# Frontend API contract

Contract version: **0.3.0**, November 19, 2026. Implemented by `cybercheck/api.py` and `cybercheck/schemas.py`. Interactive documentation: `http://127.0.0.1:8000/docs`; machine-readable schema: `GET /openapi.json`. Keep these schemas and this guide synchronized when changing the contract. The presentation website is separate from the operational interface.

## Setup and authentication

Start the API and worker as described in the [README](../README.md#run-the-project). Both processes must use the same data directory. A stopped worker leaves requests queued; the API does not execute scans itself. Basic web jobs do not require GitHub credentials or external scanner installations. Repository jobs require the configured GitHub App and repository scanners.

The local base URL is `http://127.0.0.1:8000`. Two mutually exclusive authentication modes are supported. Without OAuth configuration, every `/api/` route requires `Authorization: Bearer <operator-token>` and accesses only the operator's history. With GitHub user login configured, these routes require an HttpOnly session cookie; the operator token cannot bypass login. History, reports, deletion, and active-job deduplication are isolated by the stable GitHub user ID. Repository and website jobs both follow ownership checks. A different owner's report returns `404`. `/health`, `/docs`, `/openapi.json`, and the OAuth start/callback routes are public. Keep execution local; this change does not establish production readiness.

Never embed the real operator token in committed frontend files, a public build, URLs, or logs. The GitHub App private key stays in the backend. For a separate local frontend origin, configure the exact origin in `CYBERCHECK_CORS_ORIGINS`, for example `http://localhost:5173`; restart the API after changing it. CORS exposes the `Location` response header. It does not replace authentication.

### GitHub user login

Configure the existing GitHub App as described in [GITHUB.md](GITHUB.md#enable-user-login). Navigate the browser to `GET /auth/github/start`; do not fetch the redirect as an AJAX request. The server uses browser-bound, single-use state and PKCE S256. GitHub redirects to `/auth/github/callback`, and successful login sets an opaque HttpOnly, SameSite=Lax cookie and redirects to `/docs`. HTTPS origins receive Secure cookies. No GitHub access token is returned to browser JavaScript.

Read `GET /auth/me` after login:

```json
{"mode":"github","user":{"id":123,"login":"octocat"},"csrf_token":"<session-specific-token>"}
```

Send `X-CSRF-Token` with the returned value on every authenticated `POST` and `DELETE`, including `/auth/logout`. Missing/incorrect tokens or unapproved Origin headers return `403`. Read the CSRF token again after signing in; a new session has a new token. The header is exposed as an optional parameter in OpenAPI for manual Swagger testing. Operator mode returns `{"mode":"operator","user":null,"csrf_token":null}` and retains Bearer authentication without CSRF headers.

For a separate configured frontend origin, use `fetch(url, {credentials: "include", ...})`; CORS permits credentials only for exact configured origins, with wildcards rejected in GitHub mode. Use the same hostname (`localhost` or `127.0.0.1`) on both local servers so SameSite cookies work. A same-origin proxy is also suitable. The operational frontend still needs to connect this flow; its simulated adapter has not been replaced.

List `GET /api/github/installations?page=1`, choose an accessible installation, and list `GET /api/repositories?installation_id=50&page=1`. Each installation has `id`, `account`, and `suspended`; disable selection of suspended entries. Both lists use pages of up to 100 entries; stop pagination when the page is empty or the listed count reaches `total_count`. Users without an accessible installation must install the App on selected repositories or ask the owner to grant access. Authorizing login alone does not install the App. Repository resolution and downloads use the user token, so GitHub enforces both the user's and App's permissions.

`POST /auth/logout` returns `204`, deletes the current local session, and clears its cookie. Sessions expire no later than the GitHub token or eight hours. Refresh tokens are discarded: sign in again after expiration. A queued repository job needs an active session for its owner; the worker fails safely if none exists and never falls back to the organization's installation token. Logout affects only that browser's session; another active session for the same user may still authorize their queued jobs. GitHub revocation is enforced on subsequent GitHub requests. It does not delete the user's stored reports.

Existing history is transactionally assigned to the legacy operator during migration and is not claimed by the first GitHub login. Stop API and worker before upgrading, then restart both with the same data directory and session key. New user-owned jobs and reports are not visible in operator mode.

## Routes

| Method and path | Successful response | Purpose |
| --- | --- | --- |
| `GET /health` | `200`, `{"status":"ok"}` | API liveness; does not establish worker or scanner readiness |
| `GET /auth/github/start` | `302` to GitHub | Start browser login when OAuth is configured; otherwise `503` |
| `GET /auth/github/callback` | `303` to `/docs` | Complete login; invalid/denied/expired login returns a safe `400` |
| `GET /auth/me` | `200`, session identity and CSRF token | Requires the configured authentication mode |
| `POST /auth/logout` | `204` | Delete this browser's session; requires CSRF in GitHub mode |
| `GET /api/github/installations?page=1` | `200`, installation page | GitHub mode only; operator mode returns `409` |
| `GET /api/repositories?page=1&installation_id=50` | `200`, repository page | GitHub mode requires installation selection; operator mode uses the configured installation |
| `POST /api/analyses` | `202`, analysis acceptance | Queue a repository revision, preserving the existing route and request fields |
| `POST /api/web-analyses` | `202`, analysis acceptance | Queue basic checks for one authorized public website URL |
| `GET /api/analyses?limit=50&offset=0` | `200`, `{"analyses":[...]}` | Shared history, newest creation first; `limit` is 1–100, `offset` is nonnegative |
| `GET /api/analyses/{id}` | `200`, `{"analysis":{...},"groups":{...}}` | Poll execution state or read the final report |
| `DELETE /api/analyses/{id}` | `204`, empty body | Delete a queued or terminal job and its report; running jobs return `409` |

History currently includes complete analysis objects, not lightweight summaries. Findings are stored once in `analysis.findings`; `groups` is the same data grouped by category and sorted within each category by priority. An empty group map is `{}`. Do not add grouped and ungrouped counts together.

Repository page example:

```json
{
  "page": 1,
  "total_count": 1,
  "repositories": [
    {"id": 123, "full_name": "team/project", "private": true, "default_branch": "main"}
  ]
}
```

Request additional repository pages until the listed count reaches `total_count` or a page is empty. For history, increment `offset` by `limit`; fewer than `limit` entries indicates the end of the current list. Refresh from offset zero after creating or deleting a job.

## Requesting an analysis

Repository request:

```json
{
  "repository_id": 123,
  "reference": "main",
  "authorization_confirmed": true,
  "dependency_lookup": false
}
```

`repository_id` must come from the authorized repository list. `reference` is optional; omission uses the default branch. The backend resolves the exact SHA before queueing. Set `dependency_lookup` to `true` only after authorizing external dependency metadata queries. Its default is `false`; this causes that check to be skipped, with an explanation in the report.

Website request:

```json
{
  "target_url": "https://your-authorized-site.example/",
  "authorization_confirmed": true
}
```

Require the user to confirm ownership or written authorization before submitting either kind. The backend rejects missing/false confirmation. Both authorization confirmations and `dependency_lookup` must be JSON booleans; strings such as `"true"` are rejected. Unknown request fields are rejected.

Website URLs are normalized. Only HTTP(S), standard ports, and URLs without credentials, query strings, or fragments are accepted. Paths are retained: do not submit secret-bearing paths. Syntax is validated before queueing; DNS and network restrictions are enforced **by the worker on each connection**, not by the request handler. A syntactically valid URL can therefore be accepted and later fail because its address is private, unavailable, or out of scope. Never present `202` as proof that the destination passed network validation.

Both POST routes return `202` and a `Location: /api/analyses/{id}` header. They return `{"analysis":{...},"created":true}` for a new job. Repeating an active repository SHA or normalized web URL returns the existing job with `created:false`, still with `202`. No second job is queued. A new analysis can be requested after the previous job ends. Repository deduplication retains the first request's dependency-lookup setting; inspect the returned object.

Example acceptance for a website:

```json
{
  "analysis": {
    "id": "9dd81ab2-d3c8-4dc5-8849-b7962040ed12",
    "kind": "web",
    "repository_id": null,
    "repository": null,
    "commit_sha": null,
    "requested_ref": null,
    "target_url": "https://your-authorized-site.example/",
    "status": "queued",
    "created_at": "2026-11-18T15:00:00+00:00",
    "started_at": null,
    "finished_at": null,
    "dependency_lookup": false,
    "findings": [],
    "checks": [],
    "requests": [],
    "limitations": [],
    "error": null
  },
  "created": true
}
```

`kind` is `repository` or `web`. Repository jobs have repository identity, requested reference, and the full commit SHA; `target_url` is null. Web jobs have `target_url` and null repository/revision fields. The shared job ID is a UUID. All timestamps are UTC ISO 8601 strings with an explicit offset; unrecorded timestamps are null. `started_at` records when the worker claimed the job.

## Progress and terminal states

Poll `GET /api/analyses/{id}` about every two seconds while its status is `queued` or `running`. Stop polling on a terminal state, deletion, or authentication failure. There is no percentage progress, per-tool live stream, cancellation of running jobs, or push-notification endpoint.

| Status | Terminal? | Meaning |
| --- | --- | --- |
| `queued` | No | Waiting for the worker |
| `running` | No | Claimed by the worker; report may still be empty |
| `completed` | Yes | Configured checks finished; findings may exist |
| `partial` | Yes | Useful results exist, but coverage is incomplete |
| `failed` | Yes | Analysis could not provide the required assessment; inspect errors/checks and retain any reported findings |

On startup, the worker marks interrupted `running` jobs as `failed`; it does not silently rerun them. The operator may request a new analysis. A partial or failed analysis may still contain findings. An empty findings array, including for a failed job, is never proof of security.

## Findings and coverage

Every finding includes `tool`, `rule_id`, `category`, `title`, nullable `path` and `line`, `severity`, `priority`, `confidence`, `status`, `priority_reason`, `recommendation`, and `evidence`. Current finding `status` is `potential`; none is automatically a confirmed exploit.

Example web finding:

```json
{
  "tool": "cybercheck-web",
  "rule_id": "WEB-CSP",
  "category": "web_headers",
  "title": "No enforced Content Security Policy observed",
  "path": null,
  "line": null,
  "severity": "low",
  "priority": "review",
  "confidence": "high",
  "status": "potential",
  "priority_reason": "Observed response configuration; impact depends on application context. Review required.",
  "recommendation": "Design and test a Content Security Policy suitable for the page; report-only policies do not enforce it.",
  "evidence": {
    "url": "https://your-authorized-site.example/",
    "header": "content-security-policy",
    "configured": false
  }
}
```

Sort priorities in this order: `critical`, `high`, `medium`, `low`, `review`. Confidence is separate: current values include `high`, `medium`, `low`, `unknown`, and `version_match`. Severity is the tool's reported severity, possibly `unknown`. Preserve the supplied uncertainty and explanation. There is no project score.

Current categories include `sql_injection`, `command_injection`, `unsafe_execution`, `unsafe_deserialization`, `insecure_configuration`, `exposed_secret`, `vulnerable_dependency`, `web_transport`, `web_headers`, and `web_cookies`. Render an understandable fallback for new categories, rule IDs, and evidence keys. Evidence is a JSON object whose fields depend on the tool; do not assume a fixed shape or render strings as HTML.

`analysis.checks` reports coverage. Each entry has `status` (`completed`, `partial`, `failed`, or `skipped`) and identifies either a repository `tool` or a web `check`. Optional fields are `version`, `url`, `error`, and `note`; fields not applicable may be null. Show skipped/failed checks and their explanations independently of findings.

Web `analysis.requests` contains only observed response metadata: `url`, `status_code`, and nullable `tls` (`certificate_verified`, `version`). `analysis.limitations` lists scope restrictions. The API retains neither response bodies nor raw cookie values. Basic checks make unauthenticated GET requests, do not crawl or submit forms, and do not inject payloads. **ZAP and testssl.sh remain laboratory-only CLI tools and are not exposed through this API.**

## Errors

| HTTP status | Frontend handling |
| --- | --- |
| `401` | Missing/invalid operator token; request authentication again |
| `404` | Analysis is absent or was deleted; refresh history |
| `409` | Analysis is running and cannot be deleted; continue polling |
| `422` | Invalid request, identifier, pagination, or missing authorization confirmation |
| `403` | Missing/invalid CSRF token or unapproved request origin in GitHub session mode |
| `429` | Shared queue capacity reached (20 queued/running jobs); wait before retrying |
| `502` | GitHub access/configuration/network failure; display the safe message |

Runtime website failures normally appear in the persisted job and its checks after `202`, rather than as HTTP errors from POST. Handle unexpected server/network errors with a retry option; do not assume a malformed/non-JSON response follows the API's error shape.

Application errors use `{"detail":"Message."}`. Validation errors use the shape below; `loc` identifies the field. They deliberately omit raw input and validation context to avoid echoing credentials or submitted URLs. Use HTTP status and field locations for logic rather than matching English message text.

```json
{
  "detail": [
    {"loc": ["body", "target_url"], "msg": "Value error, Invalid website URL.", "type": "value_error"}
  ]
}
```

Do not call `response.json()` after a successful `204` deletion. Confirm deletion in the interface before sending DELETE. Deleting a queued job prevents its execution; deleting a terminal job removes its stored report.

## Existing data and validation

The store automatically migrates the original repository-only database transactionally, preserving IDs, revision identities, status, timestamps, findings, checks, and errors. Stop both processes before upgrading and take a private backup of valuable data. Upgrade API and worker together; do not run old workers against the new schema.

Contract checks cover authentication, normalization, rejected inputs without raw-input disclosure, OpenAPI schemas, CORS, shared queue capacity, deduplication, migration, and deletion. OAuth tests use controlled GitHub responses for PKCE, state replay/expiry, encrypted sessions, two-user isolation, private access, logout/revocation, and worker authorization. Real loopback HTTP/TLS tests exercise API → queue → worker → persisted report → history → deletion. Their network overrides are test-only; public-site address restrictions remain enabled. Live OAuth activation and browser integration still require the App's client credentials and callback configuration. These tests do not establish production hosting or coverage of a real external website.

## Frontend integration and local consolidation

`GET /api/auth/status` exposes only login availability and the public installation link. `GET /auth/github/setup` is a navigation-only return to `/app/#integrations`, with no installation binding or query-parameter trust. The application is at `/app/`; `?demo=1` keeps the same UI in simulated mode. The root `/` redirects to `/app/` for compatibility with previous local links.

The local schema migration maps `owner_id` to the canonical `owner="github:<id>"` and preserves report IDs and contents. See [the consolidation guide](GITHUB-INTEGRATION.md).
