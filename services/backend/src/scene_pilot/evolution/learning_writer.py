from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from scene_pilot.evolution.promotion import evaluate_trial_metrics
from scene_pilot.models.domain import AgentLearning, EvolutionArtifact, PromptOverlayRevision, Skill


class LearningWriter:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def record_learning(
        self,
        *,
        content: str,
        tags: list[str],
        promote: bool = False,
        skill_name: str | None = None,
        trial_metrics: dict[str, Any] | None = None,
        job_description_id: str | None = None,
        artifact_kind: str | None = None,
    ) -> dict[str, Any]:
        with self.session_factory() as session:
            learning = AgentLearning(content=content, tags=list(tags))
            session.add(learning)

            skill: Skill | None = None
            promotion_decision: dict[str, Any] | None = None
            if promote:
                resolved_skill_name = skill_name or "trial-skill"
                skill = self._upsert_skill(session, resolved_skill_name, content)
                merged_metrics = _merge_trial_metrics(dict(skill.trial_metrics or {}), dict(trial_metrics or {}))
                promotion_decision = evaluate_trial_metrics(merged_metrics)
                skill.trial_metrics = promotion_decision
                skill.status = "active" if bool(promotion_decision["auto_promote"]) else "trial"

            revision: PromptOverlayRevision | None = None
            if job_description_id is not None:
                revision = self._create_prompt_revision(session, job_description_id, content, dict(trial_metrics or {}))

            resolved_artifact_kind = artifact_kind or ("skill_draft" if promote else "prompt_lesson")
            artifact = EvolutionArtifact(
                artifact_kind=resolved_artifact_kind,
                title=skill_name or "learning-artifact",
                status="auto_promoted" if promotion_decision and promotion_decision["auto_promote"] else "pending_review",
                artifact_body={
                    "content": content,
                    "tags": tags,
                    "trial_metrics": trial_metrics or {},
                    "job_description_id": job_description_id,
                },
                related_skill_id=None if skill is None else skill.id,
            )
            session.add(artifact)
            session.commit()
            session.refresh(artifact)
            return {
                "learning_id": learning.id,
                "artifact_id": artifact.id,
                "skill_id": None if skill is None else skill.id,
                "prompt_revision_id": None if revision is None else revision.id,
                "auto_promoted": bool(promotion_decision and promotion_decision["auto_promote"]),
                "queued": not bool(promotion_decision and promotion_decision["auto_promote"]),
            }

    def _upsert_skill(self, session: Session, skill_name: str, content: str) -> Skill:
        stmt = select(Skill).where(Skill.skill_id == skill_name)
        skill = session.scalars(stmt).first()
        if skill is None:
            skill = Skill(
                skill_id=skill_name,
                name=skill_name,
                status="trial",
                trigger_hint=skill_name,
                body={"content": content},
                strategy={"content": content},
            )
            session.add(skill)
            session.flush()
        else:
            skill.body = {"content": content}
            skill.strategy = {"content": content}
        return skill

    def _create_prompt_revision(
        self,
        session: Session,
        job_description_id: str,
        content: str,
        trial_metrics: dict[str, Any],
    ) -> PromptOverlayRevision:
        next_version = int(
            session.scalar(
                select(func.max(PromptOverlayRevision.version)).where(
                    PromptOverlayRevision.job_description_id == job_description_id
                )
            )
            or 0
        ) + 1
        revision = PromptOverlayRevision(
            job_description_id=job_description_id,
            version=next_version,
            content={"content": content},
            status="trial",
            trial_metrics=_merge_trial_metrics({}, trial_metrics),
        )
        session.add(revision)
        session.flush()
        return revision


def _merge_trial_metrics(current: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    runs = int(current.get("runs") or 0) + int(incoming.get("runs") or 0)
    successes = int(current.get("successes") or 0) + int(incoming.get("successes") or 0)
    failures = int(current.get("failures") or 0) + int(incoming.get("failures") or 0)
    if runs == 0 and (successes or failures):
        runs = successes + failures
    return {"runs": runs, "successes": successes, "failures": failures}
