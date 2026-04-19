from __future__ import annotations

from scene_pilot.evolution.learning_writer import LearningWriter
from scene_pilot.evolution.queue import EvolutionQueue
from scene_pilot.models.domain import Skill

from ._helpers import make_session_factory


def test_functional_closure_evolution_is_closed_loop(tmp_path) -> None:
    session_factory = make_session_factory(tmp_path, "functional-evolution.db")
    writer = LearningWriter(session_factory)
    queue = EvolutionQueue(session_factory)

    promoted = writer.record_learning(
        content="High confidence prompt improvement.",
        tags=["prompt"],
        promote=True,
        skill_name="high-confidence-skill",
        trial_metrics={"runs": 3, "successes": 3},
    )
    queued = writer.record_learning(
        content="Needs more evidence.",
        tags=["prompt"],
        promote=True,
        skill_name="needs-review-skill",
        trial_metrics={"runs": 1, "successes": 0, "failures": 1},
    )

    with session_factory() as session:
        promoted_skill = session.get(Skill, promoted["skill_id"])
        queued_skill = session.get(Skill, queued["skill_id"])
        assert promoted_skill is not None and promoted_skill.status == "active"
        assert queued_skill is not None and queued_skill.status == "trial"
    assert any(item.id == queued["artifact_id"] for item in queue.list_pending())
