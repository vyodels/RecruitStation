from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from recruit_agent.api.deps import get_container
from recruit_agent.schemas.domain import AgentRunRead, AgentStatusRead, AgentTaskCreate, AgentTaskEnqueueRead, ApprovalRead
from recruit_agent.services.container import AppContainer
from recruit_agent.services.system_commands import SystemCommandApprovalError, SystemCommandDisabledError, SystemCommandPolicyError

router = APIRouter(prefix="/api/agent", tags=["agent"])


class SystemCommandRequest(BaseModel):
    command: list[str] = Field(min_length=1)
    rationale: str | None = None
    requested_by: str = "desktop-user"
    metadata: dict[str, Any] = Field(default_factory=dict)


class SystemCommandExecuteRequest(BaseModel):
    requested_by: str = "desktop-user"


@router.get("", response_model=AgentStatusRead)
def get_agent_status(container: AppContainer = Depends(get_container)) -> AgentStatusRead:
    return container.dashboard.build_agent_status(queue_depth=container.scheduler.queue.size())


@router.post("/tasks", response_model=AgentTaskEnqueueRead)
def enqueue_task(
    payload: AgentTaskCreate,
    container: AppContainer = Depends(get_container),
) -> AgentTaskEnqueueRead:
    task = container.agent_control.enqueue_task(
        payload.task_type,
        payload=payload.payload,
        priority=payload.priority,
        candidate_id=payload.candidate_id,
        workflow_id=payload.workflow_id,
        workflow_node_id=payload.workflow_node_id,
    )
    return AgentTaskEnqueueRead(
        task_id=task.task_id,
        task_type=task.task_type,
        priority=task.priority,
        queue_depth=container.scheduler.queue.size(),
    )


@router.post("/run-once", response_model=AgentRunRead)
def run_once(container: AppContainer = Depends(get_container)) -> AgentRunRead:
    outcome = container.agent_control.run_once()
    if outcome is None:
        return AgentRunRead(processed=False, status="idle")
    return AgentRunRead(
        processed=True,
        status=outcome.result.status,
        task_id=outcome.task.task_id,
        enqueued_follow_ups=outcome.enqueued_follow_ups,
        error=outcome.error,
    )


@router.get("/system-commands/policy")
def get_system_command_policy(container: AppContainer = Depends(get_container)) -> dict[str, Any]:
    return container.system_commands.policy_snapshot()


@router.post("/system-commands/request", response_model=ApprovalRead, status_code=201)
def request_system_command(
    payload: SystemCommandRequest,
    container: AppContainer = Depends(get_container),
) -> ApprovalRead:
    try:
        approval = container.system_commands.request_command(
            command=payload.command,
            rationale=payload.rationale,
            requested_by=payload.requested_by,
            metadata=payload.metadata,
        )
    except SystemCommandDisabledError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except SystemCommandPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApprovalRead.model_validate(approval)


@router.post("/system-commands/{approval_id}/execute", response_model=ApprovalRead)
def execute_system_command(
    approval_id: str,
    payload: SystemCommandExecuteRequest,
    container: AppContainer = Depends(get_container),
) -> ApprovalRead:
    try:
        approval = container.system_commands.execute_approval(approval_id, requested_by=payload.requested_by)
    except SystemCommandDisabledError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except SystemCommandPolicyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SystemCommandApprovalError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ApprovalRead.model_validate(approval)
