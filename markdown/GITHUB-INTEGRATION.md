# Consolidated GitHub integration

The implementation is based on `origin/main` commit `49f4ffc6b2cc5d1c72976580cc3d95d2be2c5cca` (PR #14), retaining its OAuth, session, repository access and scanner coverage model. The duplicate local authentication implementation is preserved only in the safety branch; it is not a second runtime authentication path.

## URLs and user flow

- Real application: `http://127.0.0.1:8000/app/#integrations`.
- Demo without API access: `http://127.0.0.1:8000/app/?demo=1#overview`, or the standalone static server.
- Login: `/auth/github/start`; OAuth callback: `/auth/github/callback`.
- Identity/CSRF: `/auth/me`; logout: `POST /auth/logout`.
- Available installations: `/api/github/installations`; selected installation is sent to `/api/repositories?installation_id=...`.
- Repository analyses, history, reports and deletion retain the main API contracts and owner isolation.

Integrações provides login, authorized installation selection, a link to install/manage repository authorization in GitHub, sign-out and a demo link. The main API verifies repository access with the user's GitHub App token; the worker rechecks access before downloading the exact queued SHA. Tokens and source never enter scanner environment variables.

The old `/auth/github/setup` URL remains as a navigation-only redirect to `/app/#integrations`. It does not consume, trust or save an `installation_id` from query parameters. Users select installations listed by the authenticated GitHub API. Therefore a spoofed setup callback cannot bind another installation. The OAuth callback continues to enforce main's browser-bound one-use state and PKCE S256.

## Configuration

Use the existing GitHub App. Configure `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `CYBERCHECK_SESSION_KEY` and `CYBERCHECK_PUBLIC_URL` together. `GITHUB_APP_SLUG` is used only to generate the installation link in Integrações; this machine uses `cybercheck-security`. No client credentials or PEM are embedded in the frontend.

The canonical key is now `CYBERCHECK_SESSION_KEY`. `CYBERCHECK_AUTH_KEY` is accepted as a migration alias if the canonical variable is absent. Local consolidation copies the existing key to the canonical variable without rotating it; API and worker share the same key and persistent `CYBERCHECK_DATA_DIR`. Do not change the key when updating code.

`GITHUB_APP_ID`, `GITHUB_INSTALLATION_ID`, `GITHUB_PRIVATE_KEY_PATH` and `CYBERCHECK_API_TOKEN` remain the main legacy operator settings. When GitHub login is enabled, the main API deliberately does not accept operator bearer authentication. To use operator mode, remove all OAuth settings, including any legacy encryption-key alias, and restart API and worker. Keep private files outside Git and the frontend; `.env`, `.secrets/`, `.data/` and `.tools/` are ignored.

GitHub settings:

- Callback: `http://127.0.0.1:8000/auth/github/callback` for this local origin.
- Setup: optional; the existing `http://127.0.0.1:8000/auth/github/setup` can remain because it is a navigation-only compatibility redirect.
- Disable automatic user authorization during installation; login is initiated by CyberCheck.
- Retain expiring user tokens, Contents read-only and Metadata read-only. Other permissions are unnecessary.
- Public App installation is needed only for accounts outside the owning account/organization.

Main's sessions expire after at most eight hours and require a new login; refresh tokens are not used by the consolidated runtime. Sign-out ends the current session, preserving reports. Other valid sessions for the same user may still authorize queued work. See [GITHUB.md](GITHUB.md) and [API.md](API.md) for the main contracts.

## Safe migration from the earlier local version

Before switching base, save source changes in a safety branch and back up the database with SQLite's backup API. Store `.env` and PEM backups in a private, Git-ignored directory with mode 700/600. Stop API and worker while migrating.

The store maps old `owner_id` values to main's `owner="github:<id>"`; legacy unowned reports remain `operator`. Existing analysis IDs, commit SHAs, timestamps, findings and checks remain unchanged. Never assign existing user reports to the operator during migration.

The auth layer performs a one-time transaction to move still-valid legacy session hashes into main's encrypted `user_sessions` table. Existing cookies remain usable; the frontend reads the new CSRF value from `/auth/me`. Expiry is capped by the original token/session lifetime and main's eight-hour limit. A durable migration marker prevents signed-out sessions from being re-imported on restart. The old encrypted tables remain for rollback, but are not consulted by normal authentication or workers after migration.

For this local consolidation, backups are under `.data/migration-backups/`, and the original source is in the local `backup/local-before-main-...` branch. These private backups must not be committed or published.

## Archive fix retained

The bounded ZIP receiver/extractor and regression tests are retained in `cybercheck/archives.py` and `tests/test_archives.py`: 25 MiB download, 100 MiB uncompressed total, 20 MiB per file, 5,000 entries and stage deadlines. Traversal, links, duplicate/conflicting paths, unsupported/encrypted ZIPs and damaged CRCs are rejected. The larger per-file cap supports the actual 17,096,584-byte tooling binary in Artigos Med without relaxing global bounds.

The worker records preparation stage and safe error codes. Do not enable HTTP debug logs that could expose signed redirects. Temporary source/downloads are removed after processing. Main's improved Bandit coverage accounting is preserved: absence of Python code is `skipped`, rather than a completed code assessment.

## Validation

Run `.venv/bin/python -m pytest -q` and `node --test demo-front/tests/*.test.mjs`.

`tests/test_main_consolidation.py` covers report ownership, session/CSRF conversion, encryption failures, idempotence, sign-out without session resurrection and the non-mutating setup return. Tests for main's authentication, scanner coverage and frontend adapter remain in place. Live acceptance uses the real GitHub account, the real Artigos Med archive and the installed scanners; migration tests do not replace that check.

Live consolidation acceptance on November 23, 2026: report `523c10a2-ef43-46cc-b32c-dd70bf4e7f21` re-analyzed `davibbraz/artigos_med` at SHA `8099ab92ecfecf8bce3f09fa4631529b39e8e33a` using main's user-token worker and the bounded ZIP fix. All three installed scanners completed and returned the same 12 dependency findings. The two pre-existing reports and the valid session were preserved by migration; the new report is a third history entry. The full suite passed 200 Python tests and 16 JavaScript tests. A browser check against the real local API/GitHub verified installation/repository listing, actual report/finding/history, reload, isolated sign-out and mobile layout; demo mode made no API calls. The temporary QA session was removed without ending the user's migrated session. No push was performed.
