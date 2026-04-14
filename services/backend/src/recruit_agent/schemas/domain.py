from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class FeatureFlags(BaseModel):
    enable_autonomy: bool = False
    enable_system_commands: bool = False
    enable_intranet_sync: bool = False
    enable_outbound_messaging: bool = False


class AppSettingsBase(BaseModel):
    app_name: str = "RecruitAgent"
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = 8741
    data_dir: str = "./data"
    database_url: str = "sqlite:///./recruit-agent.db"
    database_echo: bool = False
    scheduler_lock_timeout_seconds: int = 300
    approval_source: str = "desktop_app"
    default_platform: str = "boss"
    feature_flags: FeatureFlags = Field(default_factory=FeatureFlags)
    provider_config: dict[str, Any] = Field(default_factory=dict)
    intranet_sync: dict[str, Any] = Field(default_factory=dict)


class AppSettingsRead(AppSettingsBase):
    model_config = ConfigDict(from_attributes=True)


class AppSettingsUpdate(BaseModel):
    app_name: str | None = None
    environment: str | None = None
    host: str | None = None
    port: int | None = None
    data_dir: str | None = None
    database_url: str | None = None
    database_echo: bool | None = None
    scheduler_lock_timeout_seconds: int | None = None
    approval_source: str | None = None
    default_platform: str | None = None
    feature_flags: FeatureFlags | None = None
    provider_config: dict[str, Any] | None = None
    intranet_sync: dict[str, Any] | None = None


class CandidateBase(BaseModel):
    name: str
    platform: str = "boss"
    platform_candidate_id: str | None = None
    status: str = "discovered"
    current_workflow_node: str | None = None
    jd_id: str | None = None
    contact_info: dict[str, Any] = Field(default_factory=dict)
    resume_path: str | None = None
    online_resume_text: str | None = None
    ai_scores: dict[str, Any] = Field(default_factory=dict)
    ai_reasoning: str | None = None
    cooldown_until: datetime | None = None
    last_contacted_at: datetime | None = None


class CandidateCreate(CandidateBase):
    pass


class CandidateUpdate(BaseModel):
    name: str | None = None
    platform: str | None = None
    platform_candidate_id: str | None = None
    status: str | None = None
    current_workflow_node: str | None = None
    jd_id: str | None = None
    contact_info: dict[str, Any] | None = None
    resume_path: str | None = None
    online_resume_text: str | None = None
    ai_scores: dict[str, Any] | None = None
    ai_reasoning: str | None = None
    cooldown_until: datetime | None = None
    last_contacted_at: datetime | None = None


class CandidateRead(CandidateBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class WorkflowBase(BaseModel):
    name: str
    jd_id: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    status: str = "draft"
    version: int = 1


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(BaseModel):
    name: str | None = None
    jd_id: str | None = None
    config: dict[str, Any] | None = None
    status: str | None = None
    version: int | None = None


class WorkflowRead(WorkflowBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class SkillBase(BaseModel):
    skill_id: str
    name: str
    version: int = 1
    status: str = "draft"
    bound_to_workflow_node: str | None = None
    platform: str = "boss"
    strategy: dict[str, Any] = Field(default_factory=dict)
    execution_hints: dict[str, Any] = Field(default_factory=dict)
    health_check_config: dict[str, Any] = Field(default_factory=dict)
    last_health_check: datetime | None = None
    last_health_status: str | None = None
    confirmed_by: str | None = None
    confirmed_at: datetime | None = None


class SkillCreate(SkillBase):
    pass


class SkillUpdate(BaseModel):
    skill_id: str | None = None
    name: str | None = None
    version: int | None = None
    status: str | None = None
    bound_to_workflow_node: str | None = None
    platform: str | None = None
    strategy: dict[str, Any] | None = None
    execution_hints: dict[str, Any] | None = None
    health_check_config: dict[str, Any] | None = None
    last_health_check: datetime | None = None
    last_health_status: str | None = None
    confirmed_by: str | None = None
    confirmed_at: datetime | None = None


class SkillRead(SkillBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class SkillHealthCheckRequest(BaseModel):
    observed_result: dict[str, Any] = Field(default_factory=dict)


class SkillHealthCheckRead(BaseModel):
    skill_id: str
    status: str
    health: str
    checked_at: datetime
    issues: list[str] = Field(default_factory=list)


class LearningDraftBase(BaseModel):
    content: str
    tags: list[str] = Field(default_factory=list)
    source_task_id: str | None = None
    consolidated_at: datetime | None = None
    is_active: bool = True


class LearningDraftCreate(LearningDraftBase):
    pass


class LearningDraftUpdate(BaseModel):
    content: str | None = None
    tags: list[str] | None = None
    source_task_id: str | None = None
    consolidated_at: datetime | None = None
    is_active: bool | None = None


class LearningDraftRead(LearningDraftBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class ApprovalBase(BaseModel):
    target_type: str
    target_id: str
    title: str
    status: str = "pending"
    requested_by: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    notes: str | None = None


class ApprovalCreate(ApprovalBase):
    pass


class ApprovalUpdate(BaseModel):
    target_type: str | None = None
    target_id: str | None = None
    title: str | None = None
    status: str | None = None
    requested_by: str | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    payload: dict[str, Any] | None = None
    notes: str | None = None


class ApprovalRead(ApprovalBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class MetricsSummary(BaseModel):
    candidate_count: int
    workflow_count: int
    skill_count: int
    approval_count: int
    pending_approval_count: int
    active_skill_count: int
    by_status: dict[str, int] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str = "ready"


class ApprovalDecisionRequest(BaseModel):
    reviewer: str = Field(default="desktop-user", validation_alias=AliasChoices("reviewer", "reviewed_by"))
    reason: str | None = Field(default=None, validation_alias=AliasChoices("reason", "notes"))


class ProviderConfigRead(BaseModel):
    kind: str
    name: str
    model: str
    enabled: bool
    temperature: float = 0.2
    baseUrl: str | None = None


class ProviderConfigUpdate(BaseModel):
    kind: str
    name: str
    model: str
    enabled: bool
    temperature: float = 0.2
    baseUrl: str | None = None


class IntranetSyncConfigRead(BaseModel):
    enabled: bool
    baseUrl: str | None = None
    apiPath: str
    timeoutSeconds: int


class IntranetSyncConfigUpdate(BaseModel):
    enabled: bool | None = None
    baseUrl: str | None = None
    apiPath: str | None = None
    timeoutSeconds: int | None = None


class PlatformSettingsRead(BaseModel):
    name: str
    account: str
    cooldownDays: int
    allowOutboundMessaging: bool


class PlatformSettingsUpdate(BaseModel):
    name: str | None = None
    account: str | None = None
    cooldownDays: int | None = None
    allowOutboundMessaging: bool | None = None


class SettingsSnapshotRead(BaseModel):
    locale: str
    timezone: str
    intranetEnabled: bool
    desktopApprovalsOnly: bool
    providers: list[ProviderConfigRead]
    intranetSync: IntranetSyncConfigRead
    platform: PlatformSettingsRead
    approval_source: str | None = None
    feature_flags: FeatureFlags | None = None
    provider_config: dict[str, Any] = Field(default_factory=dict)


class SettingsSnapshotUpdate(BaseModel):
    locale: str | None = None
    timezone: str | None = None
    intranetEnabled: bool | None = None
    desktopApprovalsOnly: bool | None = None
    approval_source: str | None = None
    feature_flags: FeatureFlags | None = None
    provider_config: dict[str, Any] | None = None
    providers: list[ProviderConfigUpdate] | None = None
    intranetSync: IntranetSyncConfigUpdate | None = None
    platform: PlatformSettingsUpdate | None = None


class MetricCardRead(BaseModel):
    label: str
    value: str
    delta: str
    tone: str
    caption: str


class PipelineStageRead(BaseModel):
    label: str
    value: int
    target: int | None = None


class TimelineEventRead(BaseModel):
    id: str
    label: str
    detail: str
    at: str
    tone: str


class CandidateDashboardRead(BaseModel):
    id: str
    name: str
    title: str
    platform: str
    location: str
    status: str
    workflowNode: str
    jdTitle: str
    matchScore: int
    experienceYears: int
    nextAction: str
    summary: str
    tags: list[str] = Field(default_factory=list)
    resumeAvailable: bool
    cooldownUntil: str | None = None
    lastContactedAt: str | None = None


class WorkflowNodeSummaryRead(BaseModel):
    id: str
    name: str
    kind: str
    status: str
    owner: str
    description: str


class WorkflowDashboardRead(BaseModel):
    id: str
    name: str
    jdTitle: str
    status: str
    version: str
    updatedAt: str
    nodes: list[WorkflowNodeSummaryRead]


class SkillDashboardRead(BaseModel):
    id: str
    name: str
    version: str
    status: str
    boundNode: str
    platform: str
    health: str
    lastCheckedAt: str
    summary: str


class ApprovalDashboardRead(BaseModel):
    id: str
    kind: str
    title: str
    detail: str
    requester: str
    status: str
    createdAt: str


class AgentStatusRead(BaseModel):
    status: str
    active_task: str = Field(serialization_alias="activeTask")
    browser_lock: str = Field(serialization_alias="browserLock")
    uptime: str
    queue_depth: int = Field(serialization_alias="queueDepth")
    token_budget_used: int = Field(serialization_alias="tokenBudgetUsed")
    health: str

    model_config = ConfigDict(populate_by_name=True)


class DashboardRead(BaseModel):
    metrics: list[MetricCardRead]
    pipeline: list[PipelineStageRead]
    timeline: list[TimelineEventRead]
    alerts: list[TimelineEventRead]
    candidates: list[CandidateDashboardRead]
    workflows: list[WorkflowDashboardRead]
    skills: list[SkillDashboardRead]
    approvals: list[ApprovalDashboardRead]
    agent: AgentStatusRead
    settings: SettingsSnapshotRead


class AgentTaskCreate(BaseModel):
    task_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = 100
    candidate_id: str | None = None
    workflow_id: str | None = None
    workflow_node_id: str | None = None


class AgentTaskEnqueueRead(BaseModel):
    task_id: str
    task_type: str
    priority: int
    queue_depth: int


class AgentRunRead(BaseModel):
    processed: bool
    status: str
    task_id: str | None = None
    enqueued_follow_ups: int = 0
    error: str | None = None
