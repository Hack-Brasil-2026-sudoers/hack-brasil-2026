import secrets
from pathlib import Path
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import APIKeyCookie, HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .auth import Auth, SESSION_COOKIE, STATE_COOKIE, digest
from .config import Settings
from .github import GitHub, GitHubError
from .scanners import PRIORITIES
from .schemas import AnalysisAccepted, AnalysisHistory, AnalysisReport, ErrorResponse, Health, InstallationPage, LoginSession, RepositoryPage
from .store import QueueFull, Store
from .web import normalize_url


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    repository_id: int = Field(gt=0)
    reference: str | None = Field(default=None, min_length=1, max_length=200, pattern=r"^[^\x00-\x20\x7f]+$")
    authorization_confirmed: bool = Field(default=False, strict=True)
    dependency_lookup: bool = Field(default=False, strict=True)


class WebAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_url: str = Field(min_length=1, max_length=2048, description="Public HTTP(S) URL; standard ports only.")
    authorization_confirmed: bool = Field(default=False, strict=True)

    @field_validator("target_url")
    @classmethod
    def validate_target(cls, value):
        return normalize_url(value)


def create_app(settings=None, github=None, auth_transport=None):
    settings = settings or Settings.from_env()
    store = Store(settings.data_dir)
    github = github or GitHub(settings)
    auth = Auth(settings, store, auth_transport)
    app = FastAPI(title="CyberCheck API", version="0.3.0",
                  description="Queued repository and website checks with optional GitHub user login, without scores.",
                  responses={code: {"model": ErrorResponse} for code in (400, 401, 403, 404, 409, 422, 429, 502, 503)})
    app.state.store = store
    app.state.auth = auth
    security = APIKeyCookie(name=SESSION_COOKIE, auto_error=False) if auth.enabled else HTTPBearer(auto_error=False)

    def authenticate(request: Request, credentials: Annotated[HTTPAuthorizationCredentials | str | None, Depends(security)],
                     csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None):
        if auth.enabled:
            try:
                identity = auth.current(request.cookies.get(SESSION_COOKIE))
            except GitHubError as exc:
                raise HTTPException(401, str(exc)) from exc
            if not identity:
                raise HTTPException(401, "Sign in with GitHub.")
            if request.method not in ("GET", "HEAD", "OPTIONS"):
                origin = request.headers.get("origin")
                if origin and origin not in (settings.public_url, *settings.cors_origins):
                    raise HTTPException(403, "This request origin is not allowed.")
                if not secrets.compare_digest(digest(csrf_token or ""), digest(identity["csrf_token"])):
                    raise HTTPException(403, "Missing or invalid CSRF token.")
            return identity
        if not credentials or not secrets.compare_digest(credentials.credentials.encode(), settings.api_token.encode()):
            raise HTTPException(401, "Invalid or missing API token.", headers={"WWW-Authenticate": "Bearer"})
        return {"owner": "operator", "token": None}

    def github_for(identity):
        return GitHub(settings, auth_transport, user_token=identity["token"]) if identity["token"] else github

    protected = [Depends(authenticate)]
    if settings.cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                           allow_methods=["GET", "POST", "DELETE"],
                           allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
                           allow_credentials=auth.enabled, expose_headers=["Location"])

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Validation responses must not echo submitted URLs, credentials, or other raw input.
        issues = [{key: issue[key] for key in ("loc", "msg", "type")} for issue in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": issues})

    @app.middleware("http")
    async def response_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.get("/auth/github/start", status_code=302, response_class=RedirectResponse)
    def login():
        if not auth.enabled:
            raise HTTPException(503, "GitHub user login is not configured.")
        state, url = auth.begin()
        response = RedirectResponse(url, status_code=302)
        response.set_cookie(STATE_COOKIE, state, max_age=600, httponly=True,
                            secure=settings.public_url.startswith("https:"), samesite="lax", path="/auth/github")
        return response

    @app.get("/auth/github/callback", status_code=303, response_class=RedirectResponse)
    def callback(request: Request, code: str = Query(default="", max_length=512),
                 state: str = Query(default="", max_length=200)):
        if not auth.enabled:
            raise HTTPException(503, "GitHub user login is not configured.")
        try:
            session, lifetime = auth.complete(code, state, request.cookies.get(STATE_COOKIE))
        except GitHubError:
            response = JSONResponse(status_code=400, content={"detail": "GitHub login failed. Start again."})
        else:
            auth.logout(request.cookies.get(SESSION_COOKIE))
            response = RedirectResponse("/app/", status_code=303)
            response.set_cookie(SESSION_COOKIE, session, max_age=lifetime, httponly=True,
                                secure=settings.public_url.startswith("https:"), samesite="lax", path="/")
        response.delete_cookie(STATE_COOKIE, path="/auth/github")
        return response

    @app.get("/auth/me", response_model=LoginSession)
    def me(identity: Annotated[dict, Depends(authenticate)]):
        return {"mode": "github" if auth.enabled else "operator",
                "user": {"id": identity["id"], "login": identity["login"]} if auth.enabled else None,
                "csrf_token": identity.get("csrf_token")}

    @app.post("/auth/logout", status_code=204)
    def logout(request: Request, identity: Annotated[dict, Depends(authenticate)]):
        if auth.enabled:
            auth.logout(request.cookies.get(SESSION_COOKIE))
        response = Response(status_code=204)
        response.delete_cookie(SESSION_COOKIE, path="/")
        return response

    @app.get("/api/github/installations", dependencies=protected, response_model=InstallationPage)
    def installations(identity: Annotated[dict, Depends(authenticate)], page: int = Query(default=1, ge=1)):
        if not auth.enabled:
            raise HTTPException(409, "Installation selection requires GitHub user login.")
        try:
            return github_for(identity).installations(page)
        except (GitHubError, httpx.HTTPError) as exc:
            raise HTTPException(502, str(exc) if isinstance(exc, GitHubError) else "Failed to connect to GitHub.") from exc

    @app.get("/health", response_model=Health)
    def health():
        return {"status": "ok"}

    @app.get("/api/repositories", dependencies=protected, response_model=RepositoryPage)
    def repositories(identity: Annotated[dict, Depends(authenticate)], page: int = Query(default=1, ge=1),
                     installation_id: int | None = Query(default=None, gt=0)):
        if auth.enabled and installation_id is None:
            raise HTTPException(422, "Select a GitHub App installation with installation_id.")
        try:
            return github_for(identity).repositories(page, installation_id) if auth.enabled else github.repositories(page)
        except (GitHubError, httpx.HTTPError) as exc:
            detail = str(exc) if isinstance(exc, GitHubError) else "Failed to connect to GitHub."
            raise HTTPException(502, detail) from exc

    @app.post("/api/analyses", status_code=202, dependencies=protected, response_model=AnalysisAccepted)
    def start(payload: AnalysisRequest, response: Response, identity: Annotated[dict, Depends(authenticate)]):
        if not payload.authorization_confirmed:
            raise HTTPException(422, "Confirm that you own the project or have written authorization.")
        try:
            name, sha, reference = github_for(identity).resolve(payload.repository_id, payload.reference)
            analysis, created = store.create(payload.repository_id, name, sha, reference,
                                             payload.dependency_lookup, owner=identity["owner"])
        except (GitHubError, httpx.HTTPError) as exc:
            detail = str(exc) if isinstance(exc, GitHubError) else "Failed to connect to GitHub."
            raise HTTPException(502, detail) from exc
        except QueueFull as exc:
            raise HTTPException(429, "The queue is full. Wait for pending analyses to finish.") from exc
        response.headers["Location"] = f"/api/analyses/{analysis['id']}"
        return {"analysis": analysis, "created": created}

    @app.post("/api/web-analyses", status_code=202, dependencies=protected, response_model=AnalysisAccepted)
    def start_web(payload: WebAnalysisRequest, response: Response, identity: Annotated[dict, Depends(authenticate)]):
        if not payload.authorization_confirmed:
            raise HTTPException(422, "Confirm that you own the website or have written authorization.")
        try:
            analysis, created = store.create_web(payload.target_url, owner=identity["owner"])
        except QueueFull as exc:
            raise HTTPException(429, "The queue is full. Wait for pending analyses to finish.") from exc
        response.headers["Location"] = f"/api/analyses/{analysis['id']}"
        return {"analysis": analysis, "created": created}

    @app.get("/api/analyses", dependencies=protected, response_model=AnalysisHistory)
    def history(identity: Annotated[dict, Depends(authenticate)], limit: int = Query(default=50, ge=1, le=100),
                offset: int = Query(default=0, ge=0)):
        return {"analyses": store.list(limit, offset, owner=identity["owner"])}

    @app.get("/api/analyses/{identity}", dependencies=protected, response_model=AnalysisReport)
    def report(identity: UUID, user: Annotated[dict, Depends(authenticate)]):
        analysis = store.get(str(identity), owner=user["owner"])
        if not analysis:
            raise HTTPException(404, "Analysis not found.")
        groups = {}
        for item in analysis["findings"]:
            groups.setdefault(item["category"], []).append(item)
        for group in groups.values():
            group.sort(key=lambda item: PRIORITIES[item["priority"]])
        return {"analysis": analysis, "groups": groups}

    @app.delete("/api/analyses/{identity}", status_code=204, dependencies=protected)
    def delete(identity: UUID, user: Annotated[dict, Depends(authenticate)]):
        analysis = store.get(str(identity), owner=user["owner"])
        if not analysis:
            raise HTTPException(404, "Analysis not found.")
        if not store.delete(str(identity), owner=user["owner"]):
            raise HTTPException(409, "Wait for the analysis to finish before deleting it.")
        return Response(status_code=204)

    frontend = Path(__file__).resolve().parent.parent / "demo-front"
    if frontend.is_dir():
        app.mount("/app", StaticFiles(directory=frontend, html=True), name="app")

    return app
