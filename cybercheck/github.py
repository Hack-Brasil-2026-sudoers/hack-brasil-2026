import re
import time
from pathlib import Path
from urllib.parse import quote, urlparse

import httpx
import jwt
from pydantic import ValidationError

from .config import Settings
from .schemas import InstallationPage, RepositoryPage


class GitHubError(Exception):
    """Public error message without tokens or GitHub response bodies."""


class GitHub:
    def __init__(self, settings: Settings, transport=None, *, user_token=None):
        self.settings = settings
        self.transport = transport
        self.user_token = user_token

    @staticmethod
    def payload(response):
        try:
            data = response.json()
        except ValueError as exc:
            raise GitHubError("GitHub returned an invalid response. Try again.") from exc
        if not isinstance(data, dict):
            raise GitHubError("GitHub returned an invalid response. Try again.")
        return data

    def client(self):
        return httpx.Client(timeout=30, trust_env=False, transport=self.transport,
                            headers={"Accept": "application/vnd.github+json",
                                     "X-GitHub-Api-Version": "2022-11-28"})

    def installation_token(self, repository_id=None):
        if self.user_token:
            # User tokens enforce the intersection of user and App repository access.
            return self.user_token
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
        token = self.payload(response).get("token")
        if not isinstance(token, str) or not token or any(char.isspace() for char in token):
            raise GitHubError("GitHub did not return a valid installation token.")
        return token

    def request(self, path, token, params=None):
        with self.client() as client:
            response = client.get("https://api.github.com" + path,
                                  headers={"Authorization": f"Bearer {token}"}, params=params)
        if response.status_code != 200:
            raise GitHubError("GitHub is unavailable or access has been revoked. Check permissions and try again.")
        return self.payload(response)

    def profile(self):
        result = self.request("/user", self.user_token)
        if (type(result.get("id")) is not int or result["id"] <= 0
                or not isinstance(result.get("login"), str) or not re.fullmatch(r"[\w-]{1,100}", result["login"])):
            raise GitHubError("GitHub returned an invalid user profile.")
        return {"id": result["id"], "login": result["login"]}

    def installations(self, page=1):
        result = self.request("/user/installations", self.user_token, {"per_page": 100, "page": page})
        try:
            return InstallationPage.model_validate({"total_count": result["total_count"], "page": page, "installations": [
                {"id": item["id"], "account": item["account"]["login"],
                 "suspended": item.get("suspended_at") is not None}
                for item in result["installations"]
            ]}, strict=True).model_dump()
        except (KeyError, TypeError, AttributeError, ValidationError) as exc:
            raise GitHubError("GitHub returned an invalid installation list.") from exc

    def repositories(self, page=1, installation_id=None):
        if self.user_token and installation_id is None:
            raise GitHubError("Select an accessible GitHub App installation first.")
        path = f"/user/installations/{installation_id}/repositories" if self.user_token else "/installation/repositories"
        result = self.request(path, self.installation_token(),
                              {"per_page": 100, "page": page})
        try:
            return RepositoryPage.model_validate({"total_count": result["total_count"], "page": page,
                    "repositories": [{k: repo[k] for k in ("id", "full_name", "private", "default_branch")}
                                     for repo in result["repositories"]]}, strict=True).model_dump()
        except (KeyError, TypeError, ValidationError) as exc:
            raise GitHubError("GitHub returned an invalid repository list.") from exc

    def resolve(self, repository_id, reference=None):
        token = self.installation_token(repository_id)
        repo = self.request(f"/repositories/{repository_id}", token)
        full_name = repo.get("full_name")
        if not isinstance(full_name, str) or not re.fullmatch(r"[\w.-]+/[\w.-]+", full_name):
            raise GitHubError("GitHub returned an invalid repository name.")
        ref = reference or repo.get("default_branch")
        if not isinstance(ref, str) or not ref:
            raise GitHubError("The repository has no readable default branch.")
        commit = self.request(f"/repos/{full_name}/commits/{quote(ref, safe='')}", token)
        sha = commit.get("sha")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise GitHubError("GitHub returned an invalid commit identifier.")
        return full_name, sha, ref

    def download(self, analysis, destination: Path):
        token = self.installation_token(analysis["repository_id"])
        # Recheck access in the worker; revocation must prevent execution.
        repo = self.request(f"/repositories/{analysis['repository_id']}", token)
        if repo.get("full_name") != analysis["repository"]:
            raise GitHubError("The repository has moved. Request a new analysis.")
        url = f"https://api.github.com/repos/{repo['full_name']}/zipball/{analysis['commit_sha']}"
        with self.client() as client:
            response = client.get(url, headers={"Authorization": f"Bearer {token}"})
            if response.status_code != 302:
                raise GitHubError("Could not retrieve the archive for the selected commit.")
            location = response.headers.get("location", "")
            try:
                parsed = urlparse(location)
                port = parsed.port
            except ValueError as exc:
                raise GitHubError("Unexpected download destination; analysis blocked.") from exc
            if (parsed.scheme != "https" or parsed.hostname != "codeload.github.com"
                    or port not in (None, 443) or parsed.username or parsed.password):
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
