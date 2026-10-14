"""API request/response semalari."""
from typing import Any, Optional
from pydantic import BaseModel, Field


class RunCreate(BaseModel):
    repo: str = Field(min_length=1, description="org/repo veya repo adi")
    user_goal: str = "GitHub reposundaki son degisiklikleri incele, ilgili Jira kartlarini guncelle ve teknik bulteni hazirla."
    dry_run: bool | None = Field(default=None, description="None ise policy dry_run_default gecerli")
    count: int = Field(default=3, ge=1, le=20)
    github_conn_id: str = ""
    jira_conn_id: str = ""
    llm_conn_id: str = ""


class RunOut(BaseModel):
    run_id: str
    repo: str
    status: str
    dry_run: bool
    blocked_count: int = 0
    commit_count: int = 0
    created_at: str
    llm_provider: str = ""
    llm_model: str = ""
    failed_count: int = 0
    mismatch_count: int = 0


class CommitUnitOut(BaseModel):
    sha: Optional[str] = None
    short_sha: Optional[str] = None
    message: Optional[str] = None
    author: Optional[str] = None
    jira_ids: list[str] = []
    review_status: Optional[str] = None
    review_comment: Optional[str] = None
    affected_file: Optional[str] = None
    jira_people: dict[str, dict[str, str]] = {}


class JiraActionOut(BaseModel):
    ticket_id: str
    commit_sha: Optional[str] = None
    review_passed: bool = True
    state: str = "planned"
    comment_ok: Optional[bool] = None
    transition_from: Optional[str] = None
    transition_to: Optional[str] = None
    transition_ok: Optional[bool] = None
    skipped_reason: Optional[str] = None
    approved_by: str = ""
    approved_at: str = ""


class RunEventOut(BaseModel):
    created_at: str
    node: str
    level: str = "info"
    message: str


class RunDetailOut(BaseModel):
    run_id: str
    repo: str
    status: str
    dry_run: bool
    created_at: str
    llm_provider: str = ""
    llm_model: str = ""
    jira_base_url: str = ""
    finished_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    final_report: Optional[str] = None
    error: Optional[str] = None
    commit_units: list[CommitUnitOut] = []
    jira_actions: list[JiraActionOut] = []
    events: list[RunEventOut] = []


class ApproveIn(BaseModel):
    approved: bool
    note: str = ""


class PolicyIn(BaseModel):
    repo: str = Field(min_length=1)
    jira_project: str = ""
    on_pass_transition: str = "In Review"
    on_fail_transition: str = "Blocked"
    auto_write_pass: bool = True
    auto_write_fail: bool = False
    require_approval: bool = True
    dry_run_default: bool = True
    github_conn_id: str = ""
    jira_conn_id: str = ""


class PolicyOut(PolicyIn):
    pass


class ConnectionIn(BaseModel):
    name: str = Field(min_length=1)
    kind: str = Field(pattern="^(github|jira|llm)$")
    base_url: str = ""
    owner: str = ""
    email: str = ""
    token: str = ""
    project_key: str = ""
    provider: str = ""
    model: str = ""
    temperature: float = 0.3
    max_tokens: int = 2048
    webhook_secret: str = ""
    is_default: bool = False


class ConnectionOut(ConnectionIn):
    id: str
    is_disabled: bool = False
    created_at: str = ""
    disabled_at: str = ""
    last_tested_at: str = ""
    last_latency_ms: int = 0
    last_test_ok: Optional[bool] = None
    last_test_status: int = 0


class HealthOut(BaseModel):
    status: str = "ok"
    version: str = "0.3.0"
    data: dict[str, Any] = {}


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: str
    username: str
    role: str
    created_at: str
    last_login_at: str = ""


class TokenOut(BaseModel):
    token: str
    user: UserOut
