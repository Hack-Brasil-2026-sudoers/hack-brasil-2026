import re
import time
from pathlib import Path
from urllib.parse import quote, urlparse

import httpx
import jwt

from .config import Settings


class GitHubError(Exception):
    """Public error message without tokens or GitHub response bodies."""


class GitHub:
    def __init__(self, settings: Settings, transport=None):
        self.settings = settings
        self.transport = transport

    def client(self):
        return httpx.Client(timeout=30, trust_env=False, transport=self.transport,
                            headers={"Accept": "application/vnd.github+json",
                                     "X-GitHub-Api-Version": "2022-11-28"})

    def installation_token(self, repository_id=None):
        s = self.settings
        if not (s.app_id.isdigit() and s.installation_id.isdigit() and s.private_key_path):
            raise GitHubError("Configure the GitHub App and its installation before accessing repositories.")
        try:
            signed = jwt.encode({"iat": int(time.time()) - 60, "exp": int(time.time()) + 540,
                                 "iss": s.app_id}, Path(s.private_key_path).read_bytes(), algorithm="RS256")
        except (OSError, ValueError, jwt.PyJWTError) as exc:
            raise GitHubError("Could not load the GitHub App private key.") from exc
        body = {"permissions": {"contents": "read", "metadata": "read"}}
        if repository_id is not None:
            body["repository_ids"] = [repository_id]
        with self.client() as client:
            response = client.post(
                f"https://api.github.com/app/installations/{s.installation_id}/access_tokens",
                headers={"Authorization": f"Bearer {signed}"}, json=body,
            )
        if response.status_code != 201:
            raise GitHubError("GitHub denied access to the installation or selected repository.")
        return response.json()["token"]

    def request(self, path, token, params=None):
        with self.client() as client:
            response = client.get("https://api.github.com" + path,
                                  headers={"Authorization": f"Bearer {token}"}, params=params)
        if response.status_code != 200:
            raise GitHubError("GitHub is unavailable or access has been revoked. Check permissions and try again.")
        return response.json()

    def repositories(self, page=1):
        result = self.request("/installation/repositories", self.installation_token(),
                              {"per_page": 100, "page": page})
        return {"total_count": result["total_count"], "page": page,
                "repositories": [{k: repo[k] for k in ("id", "full_name", "private", "default_branch")}
                                 for repo in result["repositories"]]}

    def resolve(self, repository_id, reference=None):
        token = self.installation_token(repository_id)
        repo = self.request(f"/repositories/{repository_id}", token)
        full_name = repo["full_name"]
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", full_name):
            raise GitHubError("GitHub returned an invalid repository name.")
        ref = reference or repo["default_branch"]
        commit = self.request(f"/repos/{full_name}/commits/{quote(ref, safe='')}", token)
        sha = commit["sha"]
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise GitHubError("GitHub returned an invalid commit identifier.")
        return full_name, sha, ref

    def download(self, analysis, destination: Path):
        token = self.installation_token(analysis["repository_id"])
        # Recheck access in the worker; revocation must prevent execution.
        repo = self.request(f"/repositories/{analysis['repository_id']}", token)
        if repo["full_name"] != analysis["repository"]:
            raise GitHubError("The repository has moved. Request a new analysis.")
        url = f"https://api.github.com/repos/{repo['full_name']}/zipball/{analysis['commit_sha']}"
        with self.client() as client:
            response = client.get(url, headers={"Authorization": f"Bearer {token}"})
            if response.status_code != 302:
                raise GitHubError("Could not retrieve the archive for the selected commit.")
            location = response.headers.get("location", "")
            parsed = urlparse(location)
            if (parsed.scheme != "https" or parsed.hostname != "codeload.github.com"
                    or parsed.port not in (None, 443) or parsed.username or parsed.password):
                raise GitHubError("Unexpected download destination; analysis blocked.")
            # Do not persist the signed URL or forward the token to another host.
            with client.stream("GET", location) as archive:
                if archive.status_code != 200:
                    raise GitHubError("Failed to download the selected commit.")
                total = 0
                with destination.open("wb") as output:
                    for chunk in archive.iter_bytes():
                        total += len(chunk)
                        if total > 25 * 1024 * 1024:
                            raise GitHubError("Repository exceeds the MVP download limit of 25 MiB.")
                        output.write(chunk)
