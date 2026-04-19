from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session, sessionmaker

from scene_pilot.models.domain import Skill
from scene_pilot.skills.registry import SkillRegistry


AUTO_PROMOTE_MIN_RUNS = 3
AUTO_PROMOTE_MIN_SUCCESS_RATE = 0.8


class PromotionService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory
        self.skills = SkillRegistry(session_factory)

    def list_skills(self, *, status: str | None = None) -> list[Skill]:
        return self.skills.list_skills(status=status)

    def promote_skill(self, skill_pk: str) -> Skill:
        with self.session_factory() as session:
            skill = session.get(Skill, skill_pk)
            if skill is None:
                raise KeyError(f"unknown skill: {skill_pk}")
            skill.status = "active"
            skill.confirmed_at = datetime.now(UTC)
            skill.confirmed_by = skill.confirmed_by or "system"
            session.commit()
            session.refresh(skill)
            return skill

    def evaluate_trial_metrics(self, metrics: dict[str, object]) -> dict[str, object]:
        return evaluate_trial_metrics(metrics)


def evaluate_trial_metrics(metrics: dict[str, object]) -> dict[str, object]:
    runs = _to_int(metrics.get("runs"))
    successes = _to_int(metrics.get("successes"))
    failures = _to_int(metrics.get("failures"), default=max(runs - successes, 0))
    effective_runs = max(runs, successes + failures)
    success_rate = 0.0 if effective_runs == 0 else successes / effective_runs
    auto_promote = effective_runs >= AUTO_PROMOTE_MIN_RUNS and success_rate >= AUTO_PROMOTE_MIN_SUCCESS_RATE
    return {
        "runs": effective_runs,
        "successes": successes,
        "failures": failures,
        "success_rate": success_rate,
        "auto_promote": auto_promote,
        "thresholds": {
            "min_runs": AUTO_PROMOTE_MIN_RUNS,
            "min_success_rate": AUTO_PROMOTE_MIN_SUCCESS_RATE,
        },
    }


def _to_int(value: object, *, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default
