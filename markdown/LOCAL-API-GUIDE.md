# Run CyberCheck locally and connect GitHub

Use this guide to open `http://127.0.0.1:8000/app/#integrations`, sign in with GitHub, and analyze an authorized repository. Run every command from the repository root unless stated otherwise.

`127.0.0.1` means **your own computer**. Each teammate needs a running local backend and their own local configuration. Opening this address does not connect to another teammate's server. If running in a VM, container, or remote development environment, loopback and browser access require the corresponding environment's port forwarding; this guide assumes a browser and backend on the same machine.

## 1. Check that you have the integrated version

The GitHub-connected application is on `main`. A plain `git pull` on a feature branch updates that branch from its configured upstream; it does not automatically incorporate new commits from `main`.

Check your working tree first:

```bash
git status
git branch --show-current
git fetch origin
```

With a clean working tree, use the current main branch:

```bash
git switch main
git pull --ff-only origin main
```

Alternatively, to bring main into your current feature branch:

```bash
git merge origin/main
```

Preserve unfinished changes before switching or merging. If conflicts occur, resolve them before proceeding. Do not reset or discard someone else's work.

Verify that these files exist:

```text
cybercheck/auth.py
demo-front/api-service.js
markdown/GITHUB-INTEGRATION.md
```

## 2. Install Python dependencies

The backend requires Python 3.11+ and Linux. The scanner installer supports Linux x86_64. Windows users can use a Linux development environment such as WSL; native Windows scanner setup is not covered here.

```bash
python3 --version
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

For an existing environment, run the last command again after updating the project. There is no Node build step for this interface.

## 3. Configure GitHub login on this machine

If `.env` does not exist, copy `.env.example` to `.env`. **Do not overwrite an existing `.env`**: its session key may protect saved sessions.

Configure these values locally:

| Variable | Value or purpose |
| --- | --- |
| `GITHUB_CLIENT_ID` | Client ID of the GitHub App used by the team |
| `GITHUB_CLIENT_SECRET` | Client secret of that same GitHub App |
| `CYBERCHECK_SESSION_KEY` | Stable Fernet key shared by the local API and worker |
| `CYBERCHECK_PUBLIC_URL` | `http://127.0.0.1:8000` |
| `GITHUB_APP_SLUG` | Exact slug of your GitHub App; the documented local integration uses `cybercheck-security` |
| `CYBERCHECK_DATA_DIR` | `.data`, or the same absolute directory for API and worker |

Generate a session key **once for a new local configuration**:

```bash
.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

Paste the generated value into `CYBERCHECK_SESSION_KEY` in `.env`. Keep it stable across restarts. The older `CYBERCHECK_AUTH_KEY` name is accepted only as a fallback when the canonical variable is absent.

Obtain the App credentials from its owner through the team's private credential-sharing process, or configure an App you manage. They are not distributed by Git. Do not paste credentials into chat, source files, screenshots, or browser JavaScript.

The App owner must configure this exact user authorization callback in GitHub:

```text
http://127.0.0.1:8000/auth/github/callback
```

Use `127.0.0.1` consistently in the browser, callback, and `CYBERCHECK_PUBLIC_URL`; do not alternate with `localhost`. The App needs Contents read-only and Metadata read-only permissions and installation on the repositories you will assess. Signing in and installing the App are separate steps. Organization access may require its owner's approval.

`GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, and `CYBERCHECK_SESSION_KEY` must be configured together. The legacy `GITHUB_APP_ID`, `GITHUB_INSTALLATION_ID`, PEM path, and operator API token do not enable browser login by themselves. User login uses the GitHub App's user authorization flow; do not create a separate OAuth App for these credentials.

See [GitHub setup](GITHUB.md) and [integration details](GITHUB-INTEGRATION.md) for the full configuration.

## 4. Start the API

In terminal 1, from the repository root:

```bash
.venv/bin/python -m cybercheck api
```

Keep this terminal open. Expected startup output includes:

```text
Application startup complete.
Uvicorn running on http://127.0.0.1:8000
```

Check these addresses:

| Address | Expected behavior |
| --- | --- |
| `http://127.0.0.1:8000/health` | `{"status":"ok"}` |
| `http://127.0.0.1:8000/api/auth/status` | `github_enabled` is `true`, with the correct App installation URL |
| `http://127.0.0.1:8000/app/#integrations` | Real integration screen |
| `http://127.0.0.1:8000/docs` | API schemas and endpoint documentation |

Optional terminal check:

```bash
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/api/auth/status
```

The `#integrations` fragment is handled by the frontend; the server serves `/app/`. Do not launch the real interface using `file://`, the presentation website, or the standalone static server on port 8081. Port 8081 and `/app/?demo=1` use simulated data.

## 5. Connect GitHub and select a repository

1. Open `http://127.0.0.1:8000/app/#integrations`.
2. Use the GitHub sign-in action and complete authorization in the same browser.
3. If no installation is available, use the installation link on the integration screen and authorize the App for selected repositories you own or have permission to assess.
4. Return to CyberCheck and refresh access. Select the relevant account or organization installation.
5. Open **Repositories**, select a repository, and optionally enter a branch, tag, or commit SHA. An empty reference uses the default branch.
6. Confirm ownership or written authorization. Enable external dependency metadata lookup only if you authorize sending dependency names and versions to vulnerability databases.
7. Start the analysis and follow its progress to the report.

Only repositories accessible to both your GitHub user and the selected App installation are available. A repository being public does not automatically make it available through this integration.

## 6. Install scanners and start the worker

The API can serve the interface without scanners, but real analysis requires the worker and scanner executables.

Install the pinned scanners:

```bash
.venv/bin/python scripts/install_scanners.py
```

Set `OSV_SCANNER_BIN` and `BETTERLEAKS_BIN` in `.env` to the absolute paths of `.tools/osv-scanner` and `.tools/betterleaks` in your checkout. Bandit is installed with the Python dependencies.

In terminal 2, from the same repository root:

```bash
.venv/bin/python -m cybercheck worker
```

Keep both terminals open. API and worker must use the same `.env`, data directory, and session key. Restart both after changing configuration. Stop them with Ctrl+C before updating code or backing up an existing database.

An analysis remaining `queued` usually means the worker is not running or is using a different data directory. `partial` means one or more checks were skipped or incomplete; inspect coverage details. `completed` does not establish that the project is secure. Projects without Python files can have code analysis marked `skipped`.

## 7. Use the API directly

The complete schemas are at `/docs` and in the [API contract](API.md). The principal repository flow is:

| Method and route | Purpose |
| --- | --- |
| `GET /auth/me` | Current identity and CSRF token |
| `GET /api/github/installations` | Installations accessible to the signed-in user |
| `GET /api/repositories?installation_id=ID` | Repositories for a selected installation |
| `POST /api/analyses` | Queue a repository analysis |
| `GET /api/analyses/{id}` | Status, findings, and coverage |
| `GET /api/analyses` | Current user's analysis history |
| `DELETE /api/analyses/{id}` | Delete a finished analysis |

Example request body, replacing `123` with an ID returned by the repositories endpoint:

```json
{
  "repository_id": 123,
  "reference": "main",
  "authorization_confirmed": true,
  "dependency_lookup": false
}
```

HTTP 202 means the job was accepted, not that scanners finished. Poll the report endpoint for its final status.

In GitHub login mode, requests use the browser's session cookie. POST and DELETE also require the `X-CSRF-Token` value returned by `/auth/me`. A bare curl request has no browser session. The operator Bearer token is deliberately rejected when GitHub login is enabled; the **Authorize** button in Swagger does not replace GitHub login. For initial testing, use the application, which handles cookies and CSRF. Sign in again when the session expires.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Connection refused / page cannot be reached | Start the API, keep its terminal open, and check startup errors. Verify the browser and API are on the same machine. |
| `/health` works but `/app/` returns 404 | Check that you have the integrated main version, `demo-front/index.html` exists, and the process was restarted after updating. |
| Interface shows Demo mode or fictional repositories | Open port 8000 at `/app/#integrations`; remove `?demo=1`. Port 8081 serves only the demo. |
| `github_enabled` is `false` | Configure all three OAuth/session variables and restart API and worker. |
| Startup says to configure three variables together | One or more of `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, and `CYBERCHECK_SESSION_KEY` is missing. A leftover legacy key alias can also activate this validation. |
| Invalid Fernet key | Generate a valid key for a new setup; recover the original key for an existing setup rather than rotating it casually. |
| GitHub rejects the callback or returns a login error | Verify the callback, client credentials, public URL, browser cookies, and consistent hostname. Start a fresh login instead of reusing a callback URL. |
| `/auth/me` returns 401 before login | Expected: complete GitHub sign-in. If it happens later, sign in again. |
| No installations or repositories | Verify the correct GitHub account, App installation, selected repositories, organization approval, and unsuspended access. Refresh access afterward. |
| POST or DELETE returns 403 | Use the same origin and send the current session's CSRF header. The application handles this automatically. |
| Analysis stays queued | Start one worker with the same configuration and data directory as the API. |
| Worker says another worker is running | Keep only one worker per data directory; find and stop the old process normally. Do not delete the lock file to bypass it. |
| Analysis fails or is partial | Read the report's error and checks. Verify scanner paths, session validity, repository access, and archive limits. Missing checks are not clean results. |
| Port 8000 is already in use | Stop the previous CyberCheck API process and restart the intended version. |
| `ModuleNotFoundError` | Install dependencies with `.venv/bin/python -m pip install -e '.[dev]'` and launch using that same interpreter. |

If you need help, share your branch and commit (`git log -1 --oneline`), Python version, failing URL, HTTP status, and a redacted error message. Do not share `.env`, session cookies, client secrets, PEM files, or OAuth callback query strings.
