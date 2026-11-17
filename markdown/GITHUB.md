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
- OAuth during installation, callback, and setup URL: do not configure them at this stage. The current backend authenticates the installation rather than individual users.
- Installation: only on the owning account for the organization's initial test. Access to other accounts is a separate enhancement.

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

Individual login and multiuser isolation are not implemented yet. Do not publish this single-operator backend as an open service.

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

Specific handling was added for this case, and the suite passed with 24 tests. Individual login, access to an additional private repository, and installation revocation still require their own tests.

References: [GitHub App registration](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app) and [prefilled URL parameters](https://docs.github.com/en/apps/sharing-github-apps/registering-a-github-app-using-url-parameters).
