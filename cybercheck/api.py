import secrets
from typing import Annotated
from uuid import UUID

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from .config import Settings
from .github import GitHub, GitHubError
from .scanners import PRIORITIES
from .store import QueueFull, Store


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    repository_id: int = Field(gt=0)
    reference: str | None = Field(default=None, min_length=1, max_length=200, pattern=r"^[^\x00-\x20\x7f]+$")
    authorization_confirmed: bool = False
    dependency_lookup: bool = False


def create_app(settings=None, github=None):
    settings = settings or Settings.from_env()
    store = Store(settings.data_dir)
    github = github or GitHub(settings)
    app = FastAPI(title="CyberCheck API", version="0.1.0",
                  description="Backend inicial de operador único. Analisa revisões autorizadas, sem scores.")
    app.state.store = store
    security = HTTPBearer(auto_error=False)

    def authenticate(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)]):
        if not credentials or not secrets.compare_digest(credentials.credentials, settings.api_token):
            raise HTTPException(401, "Token de API inválido ou ausente.", headers={"WWW-Authenticate": "Bearer"})

    protected = [Depends(authenticate)]
    if settings.cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins),
                           allow_methods=["GET", "POST", "DELETE"], allow_headers=["Authorization", "Content-Type"])

    @app.middleware("http")
    async def response_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/repositories", dependencies=protected)
    def repositories(page: int = Query(default=1, ge=1)):
        try:
            return github.repositories(page)
        except (GitHubError, httpx.HTTPError) as exc:
            detail = str(exc) if isinstance(exc, GitHubError) else "Falha na conexão com GitHub."
            raise HTTPException(502, detail) from exc

    @app.post("/api/analyses", status_code=202, dependencies=protected)
    def start(payload: AnalysisRequest, response: Response):
        if not payload.authorization_confirmed:
            raise HTTPException(422, "Confirme que é responsável pelo projeto ou possui autorização por escrito.")
        try:
            name, sha, reference = github.resolve(payload.repository_id, payload.reference)
            analysis, created = store.create(payload.repository_id, name, sha, reference, payload.dependency_lookup)
        except (GitHubError, httpx.HTTPError) as exc:
            detail = str(exc) if isinstance(exc, GitHubError) else "Falha na conexão com GitHub."
            raise HTTPException(502, detail) from exc
        except QueueFull as exc:
            raise HTTPException(429, "Fila cheia. Aguarde as análises pendentes.") from exc
        response.headers["Location"] = f"/api/analyses/{analysis['id']}"
        return {"analysis": analysis, "created": created}

    @app.get("/api/analyses", dependencies=protected)
    def history(limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0)):
        return {"analyses": store.list(limit, offset)}

    @app.get("/api/analyses/{identity}", dependencies=protected)
    def report(identity: UUID):
        analysis = store.get(str(identity))
        if not analysis:
            raise HTTPException(404, "Análise não encontrada.")
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
            raise HTTPException(404, "Análise não encontrada.")
        if not store.delete(str(identity)):
            raise HTTPException(409, "Aguarde o término da análise antes de excluir.")
        return Response(status_code=204)

    return app
