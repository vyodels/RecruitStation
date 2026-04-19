from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from scene_pilot.db.base import utcnow
from scene_pilot.kernel.kernel import AgentKernel
from scene_pilot.memory.service import MemoryService
from scene_pilot.models.domain import AgentRun, AgentRuntimeEvent, AgentSession, AgentTurnRecord, McpServer, Skill
from scene_pilot.runtime.limits import TurnLimits
from scene_pilot.runtime.models import GoalRef, InputEnvelope, Message, Observation, RoundOutcome


@dataclass(slots=True)
class AutonomousAgent:
    session_factory: sessionmaker[Session]
    kernel: AgentKernel
    turn_limits: TurnLimits = field(default_factory=TurnLimits)

    def run_turn_from_envelope(self, envelope: dict[str, Any]) -> RoundOutcome:
        with self.session_factory() as session:
            run = self._resolve_run(session, envelope)
            run.status = "running"
            if run.started_at is None:
                run.started_at = utcnow()
            next_seq = self._next_turn_seq(session, run.id)
            memory_service = MemoryService(session)
            agent_session = session.get(AgentSession, run.session_id)
            agent_profile_id = None if agent_session is None else agent_session.agent_profile_id
            turn = AgentTurnRecord(
                run_pk=run.id,
                seq=next_seq,
                trigger_type=str(envelope.get("trigger_type") or "manual"),
                status="started",
                phase="sense",
            )
            session.add(turn)
            session.flush()
            session.add(
                AgentRuntimeEvent(
                    session_id=run.session_id,
                    run_id=run.id,
                    candidate_id=run.candidate_id,
                    source="autonomous",
                    event_type="turn.started",
                    message="turn started",
                    turn_id=turn.turn_id,
                    seq=next_seq,
                    payload={"trigger_type": turn.trigger_type},
                )
            )

            goal = GoalRef(
                goal_id=run.run_id or run.id,
                scope_kind=str(envelope.get("scope_kind") or run.lane or "global"),
                scope_ref=str(envelope.get("scope_ref") or run.candidate_id or run.job_description_id or run.id),
                goal_text=str(run.context_manifest.get("goal") or run.run_type or "Autonomous execution"),
                constraints={
                    "run_pk": run.id,
                    "agent_profile_id": agent_profile_id,
                    "global_scope_ref": agent_profile_id,
                    "source_kind": "autonomous",
                },
            )

            round_history: list[Message] = []
            round_seq = 0
            started_at = time.monotonic()
            last_outcome = RoundOutcome(status="continue", gate_signal="continue")
            while True:
                if round_seq >= self.turn_limits.max_rounds_per_turn:
                    last_outcome = RoundOutcome(
                        status="continue",
                        gate_signal="budget_exhausted",
                        final_output=last_outcome.final_output,
                    )
                    break
                if time.monotonic() - started_at >= self.turn_limits.turn_timeout_seconds:
                    last_outcome = RoundOutcome(
                        status="continue",
                        gate_signal="budget_exhausted",
                        final_output=last_outcome.final_output,
                    )
                    break

                round_seq += 1
                observation = Observation(
                    world_snapshot=dict(envelope.get("world_snapshot") or {}),
                    scope_kind=goal.scope_kind,
                    scope_ref=goal.scope_ref,
                    recent_events=memory_service.fetch_recent_events(run_id=run.id, limit=8),
                    available_tools=sorted(self.kernel.tool_registry.tools.keys()),
                    available_skills=self._available_skill_names(session),
                    available_mcps=self._available_mcp_names(session),
                    hash=str(envelope.get("observation_hash") or turn.turn_id),
                    input=InputEnvelope(history_messages=list(round_history)),
                )
                last_outcome = self.kernel.run_round(
                    goal=goal,
                    observation=observation,
                    limits=self.kernel.limits,
                    memory_service=memory_service,
                    learning_writer=self.kernel.learning_writer,
                )
                round_history = list(last_outcome.metadata.get("history_messages") or [])
                session.add(
                    AgentRuntimeEvent(
                        session_id=run.session_id,
                        run_id=run.id,
                        candidate_id=run.candidate_id,
                        source="autonomous",
                        event_type="round.completed",
                        message=last_outcome.final_output or last_outcome.status,
                        turn_id=turn.turn_id,
                        seq=round_seq,
                        payload={
                            "round_seq": round_seq,
                            "status": last_outcome.status,
                            "gate_signal": last_outcome.gate_signal,
                            "tool_calls": [call.to_provider_payload() for call in last_outcome.tool_calls],
                            "tool_results": [
                                {
                                    "tool_name": result.tool_name,
                                    "is_error": result.is_error,
                                    "output": result.output,
                                }
                                for result in last_outcome.tool_results
                            ],
                        },
                    )
                )
                if last_outcome.status == "cancelled" or last_outcome.gate_signal not in {None, "continue"}:
                    break

            turn.status = _turn_status_from_outcome(last_outcome)
            turn.phase = "evaluate"
            turn.outcome_kind = last_outcome.status
            turn.turn_metadata = {
                "final_output": last_outcome.final_output,
                "gate_signal": last_outcome.gate_signal,
                "round_count": round_seq,
            }
            run.turns_count = int(run.turns_count or 0) + 1
            run.status = _run_status_from_outcome(last_outcome)
            if run.status in {"completed", "waiting_human", "blocked", "cancelled"}:
                run.finished_at = utcnow()

            session.add(
                AgentRuntimeEvent(
                    session_id=run.session_id,
                    run_id=run.id,
                    candidate_id=run.candidate_id,
                    source="autonomous",
                    event_type=_terminal_event_type(last_outcome),
                    message=last_outcome.final_output or last_outcome.status,
                    turn_id=turn.turn_id,
                    seq=next_seq,
                    payload={"status": last_outcome.status, "gate_signal": last_outcome.gate_signal},
                )
            )
            session.commit()
            session.refresh(run)
            return last_outcome

    def recover_stale(self) -> int:
        with self.session_factory() as session:
            stmt = select(AgentRun).where(AgentRun.status == "running")
            recovered = 0
            for run in session.scalars(stmt).all():
                run.status = "interrupted"
                recovered += 1
            if recovered:
                session.commit()
            return recovered

    def _resolve_run(self, session: Session, envelope: dict[str, Any]) -> AgentRun:
        run_pk = str(envelope.get("run_pk") or "").strip()
        if run_pk:
            run = session.get(AgentRun, run_pk)
            if run is None:
                raise KeyError(f"unknown run: {run_pk}")
            return run
        run_id = str(envelope.get("run_id") or "").strip()
        if run_id:
            stmt = select(AgentRun).where(AgentRun.run_id == run_id)
            run = session.scalars(stmt).first()
            if run is not None:
                return run
        raise KeyError("run envelope must include run_pk or run_id")

    def _next_turn_seq(self, session: Session, run_pk: str) -> int:
        stmt = select(func.max(AgentTurnRecord.seq)).where(AgentTurnRecord.run_pk == run_pk)
        return int(session.scalar(stmt) or 0) + 1

    def _available_skill_names(self, session: Session) -> list[str]:
        stmt = select(Skill.name).where(Skill.status.in_(("trial", "active"))).order_by(Skill.name.asc())
        return [str(name) for name in session.scalars(stmt).all()]

    def _available_mcp_names(self, session: Session) -> list[str]:
        stmt = select(McpServer.name).order_by(McpServer.name.asc())
        return [str(name) for name in session.scalars(stmt).all()]


def _run_status_from_outcome(outcome: RoundOutcome) -> str:
    if outcome.status == "complete" or outcome.gate_signal == "goal_done":
        return "completed"
    if outcome.status == "wait_human" or outcome.gate_signal == "wait_human":
        return "waiting_human"
    if outcome.status == "cancelled" or outcome.gate_signal == "paused":
        return "cancelled"
    if outcome.status == "escalate" or outcome.gate_signal == "escalate":
        return "blocked"
    if outcome.gate_signal == "budget_exhausted":
        return "blocked"
    return "running"


def _turn_status_from_outcome(outcome: RoundOutcome) -> str:
    if outcome.status == "complete" or outcome.gate_signal == "goal_done":
        return "completed"
    if outcome.status == "wait_human" or outcome.gate_signal == "wait_human":
        return "waiting_human"
    if outcome.status == "cancelled" or outcome.gate_signal == "paused":
        return "cancelled"
    if outcome.status == "escalate" or outcome.gate_signal == "escalate":
        return "failed"
    if outcome.gate_signal == "budget_exhausted":
        return "failed"
    return "running"


def _terminal_event_type(outcome: RoundOutcome) -> str:
    if outcome.status == "wait_human" or outcome.gate_signal == "wait_human":
        return "turn.waiting_human"
    if outcome.status == "cancelled" or outcome.gate_signal == "paused":
        return "turn.cancelled"
    if outcome.status == "escalate" or outcome.gate_signal == "escalate":
        return "turn.failed"
    return "turn.completed"
