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


class CommitUnitOut(BaseModel):
    sha: Optional[str] = None
    short_sha: Optional[str] = None
    message: Optional[str] = None
    author: Optional[str] = None
    jira_ids: list[str] = []
    review_status: Optional[str] = None
    review_comment: Optional[str] = None
    affected_file: Optional[str] = None


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


class RunDetailOut(BaseModel):
    run_id: str
    repo: str
    status: str
    dry_run: bool
    created_at: str
    final_report: Optional[str] = None
    error: Optional[str] = None
    commit_units: list[CommitUnitOut] = []
    jira_actions: list[JiraActionOut] = []


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


class HealthOut(BaseModel):
    status: str = "ok"
    version: str = "0.2.0"
    data: dict[str, Any] = {}
