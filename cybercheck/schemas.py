"""Response contracts shared with the frontend and published in OpenAPI."""
from typing import Any, Literal

from pydantic import BaseModel, Field


AnalysisStatus = Literal["queued", "running", "completed", "partial", "failed"]
CheckStatus = Literal["completed", "partial", "failed", "skipped"]
Priority = Literal["critical", "high", "medium", "low", "review"]


class Finding(BaseModel):
    tool: str
    rule_id: str
    category: str
    title: str
    path: str | None
    line: int | None
    severity: str
    priority: Priority
    confidence: str
    status: Literal["potential"]
    priority_reason: str
    recommendation: str
    evidence: dict[str, Any]


class Check(BaseModel):
    status: CheckStatus
    tool: str | None = None
    check: str | None = None
    version: str | None = None
    url: str | None = None
    error: str | None = None
    note: str | None = None


class TLSObservation(BaseModel):
    certificate_verified: bool
    version: str | None


class WebRequestObservation(BaseModel):
    url: str
    status_code: int
    tls: TLSObservation | None


class Analysis(BaseModel):
    id: str
    kind: Literal["repository", "web"]
    repository_id: int | None
    repository: str | None
    commit_sha: str | None
    requested_ref: str | None
    target_url: str | None
    status: AnalysisStatus
    created_at: str
    started_at: str | None
    finished_at: str | None
    dependency_lookup: bool
    findings: list[Finding]
    checks: list[Check]
    requests: list[WebRequestObservation]
    limitations: list[str]
    error: str | None


class AnalysisAccepted(BaseModel):
    analysis: Analysis
    created: bool


class AnalysisHistory(BaseModel):
    analyses: list[Analysis]


class AnalysisReport(BaseModel):
    analysis: Analysis
    groups: dict[str, list[Finding]]


class Repository(BaseModel):
    id: int
    full_name: str
    private: bool
    default_branch: str


class RepositoryPage(BaseModel):
    repositories: list[Repository]
    page: int
    total_count: int


class Health(BaseModel):
    status: Literal["ok"]


class ValidationIssue(BaseModel):
    loc: list[str | int]
    msg: str
    type: str


class ErrorResponse(BaseModel):
    detail: str | list[ValidationIssue] = Field(description="Message, or input validation issues without raw input.")
