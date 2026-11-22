# GitHub App setup

## Organization registration

The App must belong to **Hack-Brasil-2026-sudoers**. The user confirmed they own the organization.

[Open the prefilled registration form](https://github.com/organizations/Hack-Brasil-2026-sudoers/settings/apps/new?name=CyberCheck%20Sudoers&url=https%3A%2F%2Fgithub.com%2FHack-Brasil-2026-sudoers%2Fhack-brasil-2026&description=Defensive%20assessment%20of%20Python%20repositories&contents=read&metadata=read&public=false&webhook_active=false&request_oauth_on_install=false).

Check before creating:

- Name: CyberCheck Sudoers; choose another available name if it is already taken.
- Homepage: the project's public repository.
- Repository permissions: **Contents: Read-only** and **Metadata: Read-only**.
- All other permissions: no access.
- Webhooks: disabled, since analyses are started manually.
- Operator-only mode needs no OAuth callback. For individual users, configure the callback and client credentials under [Enable user login](#enable-user-login). A setup URL is not required.
- The original installation was restricted to the owning organization. To let users install the App on their own accounts, allow installation on **Any account** in the App settings, keeping repository selection and read-only permissions.

The link is a guide for recreating the configuration if needed. The team's App is already registered and installed, as recorded in the status section; another App is not needed.

## Installation and local credentials

After creating the App:

1. Record the **App ID** from its settings page. Do not confuse it with the Client ID.
2. Generate a private key and download the PEM file. Keep it outside the repository in a private directory, readable only by its owner.
3. Under **Install App**, install it on the organization with **Only select repositories**, initially selecting only `hack-brasil-2026`. Add other test projects only when needed.
4. Obtain the **Installation ID** from that installation's configuration page URL.
5. Set `GITHUB_APP_ID`, `GITHUB_INSTALLATION_ID`, and `GITHUB_PRIVATE_KEY_PATH` in the local `.env`, using the absolute PEM path.

Do not send keys or tokens through chat, put them in the frontend, or add them to Git. The `.env` is ignored and contains the validated local configuration. On a new machine, configure it locally; credentials are not distributed through the repository.

## Verify the configuration

With the virtual environment installed:

```bash
.venv/bin/python -m cybercheck api
```

At `http://127.0.0.1:8000/docs`, select **Authorize**, enter the local token, and call `GET /api/repositories`. The response should list only repositories authorized for the installation.

Then validate commit resolution, download, and analysis of a project you own. Start the worker separately:

```bash
.venv/bin/python -m cybercheck worker
```

Without OAuth configuration this remains the local operator flow. For isolated user sessions, follow the section below. Keep the backend local; deployment hardening remains separate work.

## Enable user login

The backend supports user authorization on the existing **GitHub App**. Do not create a separate OAuth App or use a personal access token. User access is limited by both the user's permissions and the App's installation permissions, including selected private repositories. Login does not itself install the App.

1. In the existing App settings, add this **Callback URL** for local development: `http://127.0.0.1:8000/auth/github/callback`. Use the same hostname consistently in the browser and configuration. Leave the setup URL empty; users start authorization through the backend's login route.
2. Retain **Contents: Read-only** and **Metadata: Read-only**, with no new write permissions. Allow installation on **Any account** if users need their own account/organization repositories. The repository owner or organization administrator installs the App using **Only select repositories**.
3. Record the App's **Client ID** and generate a **Client secret**. These are separate from the App ID and private key. Configure them locally as `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET`; never send their real values through chat or commit them.
4. Generate a session encryption key locally with the command in `.env.example`, save it as `CYBERCHECK_SESSION_KEY`, and set `CYBERCHECK_PUBLIC_URL=http://127.0.0.1:8000`. All three OAuth settings must be provided together. API and worker must share the same data directory and stable session key. HTTPS is required for non-loopback origins. The `cryptography` package, already used through PyJWT's crypto extra, is now declared directly for Fernet encryption (Apache-2.0/BSD-3-Clause).
5. Stop API and worker, upgrade both together, then restart. The owner migration preserves old reports under the legacy operator; it does not assign them to a GitHub user. In OAuth mode the operator Bearer token is not accepted, and `CYBERCHECK_API_TOKEN`, the installation ID, and the App private key are not required for user authorization.
6. Open `http://127.0.0.1:8000/auth/github/start` in the browser. After authorization, the callback sets the session cookie and opens `/docs`. Call `GET /auth/me`, then use its CSRF token in the documented `X-CSRF-Token` header for writes. Read the user's installations, select one, list its accessible repositories, and submit an analysis. See [the API flow](API.md#github-user-login).

The flow uses PKCE S256, a browser-bound ten-minute single-use state, HttpOnly/SameSite=Lax cookies, and Secure cookies for HTTPS. Session identifiers are hashed in SQLite, and GitHub access tokens are encrypted with Fernet. Tokens never enter analysis records, frontend responses, or scanner environment variables. GitHub refresh tokens are discarded; sessions last at most eight hours and then require login again. Logout removes only the current browser session. Another valid session for the same user may still authorize that user's jobs.

The worker downloads the exact queued SHA using the user's GitHub token, rechecking repository access at execution time. An expired/missing session or revoked access fails the job; no organization-installation token is substituted. The operator mode remains available by removing OAuth configuration and restarting both processes; user-owned history stays isolated.

The CLI disables HTTP access logging because OAuth callbacks contain one-time codes in query parameters. If launching Uvicorn directly, use `--no-access-log`; any proxy must also omit callback query strings from logs. Do not expose the local demo publicly as part of this setup.

Automated tests use controlled GitHub responses. The current machine still needs the OAuth client credentials and callback configured before real browser login can be verified. Private access, revocation, and pagination in these tests are simulations, not evidence of a new live installation.

Official references: [user tokens, permission intersection, state and PKCE](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app), [user-accessible installations and repositories](https://docs.github.com/en/rest/apps/installations), [callback configuration](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/about-the-user-authorization-callback-url), and [token expiration](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/refreshing-user-access-tokens).

## Status

The `cybercheck-sudoers` App is registered and installed on the organization, with read-only Contents and Metadata permissions and explicit repository selection. Its IDs and RSA key path are configured in the local `.env`; the key has permission 600 and has not been copied into Git.

Live verification on November 17, 2026:

- App authentication and installation token issuance: OK.
- Listing: one authorized repository, `Hack-Brasil-2026-sudoers/hack-brasil-2026`.
- Resolution of the default `main` branch to commit `35bb2ff6d80982a08ee32d59e12de12d4df1cb79`: OK.
- Temporary download and extraction of the revision: OK; files discarded after verification.
- `GET /api/repositories` with real GitHub access: OK; requests without a local token blocked with 401.

After setup, the complete flow was also validated on branch `pedro`, commit `156862f5d413c74bd2888f4e45c594883511cc88`: authenticated API request, SQLite queue, worker, download, scanners, report retrieval, and temporary file cleanup.

Bandit and Betterleaks completed. OSV-Scanner found no supported dependency file in that revision, so the report marks the check as not performed (`skipped`) and the analysis as partial. This does not establish that dependencies have no vulnerabilities. The verification analysis remains in the local `.data/` history, outside Git.

Specific handling was added for this case, and the suite then passed with 24 tests. The later user-login implementation has separate mocked OAuth, private-access, pagination, and revocation tests; new live verification remains pending.

References: [GitHub App registration](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app) and [prefilled URL parameters](https://docs.github.com/en/apps/sharing-github-apps/registering-a-github-app-using-url-parameters).
