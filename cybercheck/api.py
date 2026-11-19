import secrets
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .config import Settings
from .github import GitHub, GitHubError
from .scanners import PRIORITIES
from .schemas import AnalysisAccepted, AnalysisHistory, AnalysisReport, ErrorResponse, Health, RepositoryPage
from .store import QueueFull, Store
from .web import normalize_url


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    repository_id: int = Field(gt=0)
    reference: str | None = Field(default=None, min_length=1, max_length=200, pattern=r"^[^\x00-\x20\x7f]+$")
    authorization_confirmed: bool = False
    dependency_lookup: bool = False


class WebAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_url: str = Field(min_length=1, max_length=2048, description="Public HTTP(S) URL; standard ports only.")
    authorization_confirmed: bool = Field(default=False, strict=True)

    @field_validator("target_url")
    @classmethod
    def validate_target(cls, value):
        return normalize_url(value)


def create_app(settings=None, github=None):
    settings = settings or Settings.from_env()
    store = Store(settings.data_dir)
    github = github or GitHub(settings)
    app = FastAPI(title="CyberCheck API", version="0.2.0",
                  description="Single-operator backend for queued repository and basic website checks without scores.",
                  responses={code: {"model": ErrorResponse} for code in (401, 404, 409, 422, 429, 502)})
    app.state.store = store
    security = HTTPBearer(auto_error=False)

    def authenticate(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)]):
        if not credentials or not secrets.compare_digest(credentials.credentials, settings.api_token):
            raise HTTPException(401, "Invalid or missing API token.", headers={"WWW-Authenticate": "Bearer"})

    protected = [Depends(authenticate)]
    if settings.cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                           allow_methods=["GET", "POST", "DELETE"], allow_headers=["Authorization", "Content-Type"],
                           expose_headers=["Location"])

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
        return response

    @app.get("/health", response_model=Health)
    def health():
        return {"status": "ok"}

    @app.get("/api/repositories", dependencies=protected, response_model=RepositoryPage)
    def repositories(page: int = Query(default=1, ge=1)):
        try:
            return github.repositories(page)
        except (GitHubError, httpx.HTTPError) as exc:
            detail = str(exc) if isinstance(exc, GitHubError) else "Failed to connect to GitHub."
            raise HTTPException(502, detail) from exc

    @app.post("/api/analyses", status_code=202, dependencies=protected, response_model=AnalysisAccepted)
    def start(payload: AnalysisRequest, response: Response):
        if not payload.authorization_confirmed:
            raise HTTPException(422, "Confirm that you own the project or have written authorization.")
        try:
            name, sha, reference = github.resolve(payload.repository_id, payload.reference)
            analysis, created = store.create(payload.repository_id, name, sha, reference, payload.dependency_lookup)
        except (GitHubError, httpx.HTTPError) as exc:
            detail = str(exc) if isinstance(exc, GitHubError) else "Failed to connect to GitHub."
            raise HTTPException(502, detail) from exc
        except QueueFull as exc:
            raise HTTPException(429, "The queue is full. Wait for pending analyses to finish.") from exc
        response.headers["Location"] = f"/api/analyses/{analysis['id']}"
        return {"analysis": analysis, "created": created}

    @app.post("/api/web-analyses", status_code=202, dependencies=protected, response_model=AnalysisAccepted)
    def start_web(payload: WebAnalysisRequest, response: Response):
        if not payload.authorization_confirmed:
            raise HTTPException(422, "Confirm that you own the website or have written authorization.")
        try:
            analysis, created = store.create_web(payload.target_url)
        except QueueFull as exc:
            raise HTTPException(429, "The queue is full. Wait for pending analyses to finish.") from exc
        response.headers["Location"] = f"/api/analyses/{analysis['id']}"
        return {"analysis": analysis, "created": created}

    @app.get("/api/analyses", dependencies=protected, response_model=AnalysisHistory)
    def history(limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0)):
        return {"analyses": store.list(limit, offset)}

    @app.get("/api/analyses/{identity}", dependencies=protected, response_model=AnalysisReport)
    def report(identity: UUID):
        analysis = store.get(str(identity))
        if not analysis:
            raise HTTPException(404, "Analysis not found.")
        groups = {}
        for item in analysis["findings"]:
            groups.setdefault(item["category"], []).append(item)
        for group in groups.values():
            group.sort(key=lambda item: PRIORITIES[item["priority"]])
        return {"analysis": analysis, "groups": groups}

    @app.delete("/api/analyses/{identity}", status_code=204, dependencies=protected)
    def delete(identity: UUID):
        analysis = store.get(str(identity))
        if not analysis:
            raise HTTPException(404, "Analysis not found.")
        if not store.delete(str(identity)):
            raise HTTPException(409, "Wait for the analysis to finish before deleting it.")
        return Response(status_code=204)

    return app
