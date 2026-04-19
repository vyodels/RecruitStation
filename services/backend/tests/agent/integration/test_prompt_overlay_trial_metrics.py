from __future__ import annotations

from pathlib import Path

from scene_pilot.evolution.prompt_evolution import PromptEvolution
from scene_pilot.models.domain import JobDescription

from ._helpers import make_session_factory


def test_prompt_overlay_trial_metrics_are_accumulated(tmp_path: Path) -> None:
    session_factory = make_session_factory(tmp_path, "prompt-evolution.db")
    with session_factory() as session:
        job = JobDescription(title="Backend Engineer")
        session.add(job)
        session.commit()
        session.refresh(job)
        job_description_id = job.job_description_id

    evolution = PromptEvolution(session_factory)
    revision = evolution.create_revision(job_description_id=job_description_id, content={"overlay": "be concise"})
    updated = evolution.record_trial_metrics(revision.id, success=True, latency_ms=120)
    updated = evolution.record_trial_metrics(updated.id, success=False, latency_ms=240)

    assert updated.trial_metrics["runs"] == 2
    assert updated.trial_metrics["successes"] == 1
    assert updated.trial_metrics["failures"] == 1
    assert updated.trial_metrics["success_rate"] == 0.5
    assert updated.trial_metrics["avg_latency_ms"] == 180
