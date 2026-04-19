from __future__ import annotations

from pathlib import Path

from scene_pilot.core.settings import AppSettings
from scene_pilot.db.session import create_engine_from_settings, create_session_factory, initialize_database
from scene_pilot.models.domain import RecruitAgentProfile
from scene_pilot.services.container import _seed_builtin_agent_profiles


def test_seed_builtin_profiles_normalizes_autonomous_memory_policy(tmp_path: Path) -> None:
    settings = AppSettings(
        data_dir=str(tmp_path / "data"),
        database_url=f"sqlite:///{tmp_path / 'builtin-agent-seed.db'}",
    )
    engine = create_engine_from_settings(settings)
    initialize_database(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        session.add(
            RecruitAgentProfile(
                agent_key="autonomous",
                name="Autonomous Agent",
                is_primary=True,
                prompt_config={},
                memory_policy={
                    "candidate_memory": {
                        "isolation": "strict_by_candidate",
                        "auto_compact": True,
                        "compact_threshold": 123,
                        "schema": ["identity_summary"],
                        "disclosure": ["preview"],
                    },
                    "job_memory": {
                        "isolation": "strict_by_jd",
                        "auto_compact": True,
                        "compact_threshold": 456,
                        "schema": ["screening_preferences"],
                        "disclosure": ["preview"],
                    },
                    "agent_global_memory": {
                        "scope": "agent_global",
                        "auto_compact": True,
                        "compact_threshold": 789,
                        "schema": ["global_strategies", "common_failures", "effective_patterns"],
                        "disclosure": ["preview"],
                    },
                },
            )
        )
        session.commit()

    _seed_builtin_agent_profiles(session_factory)

    with session_factory() as session:
        profile = session.query(RecruitAgentProfile).filter_by(agent_key="autonomous").one()
        assert profile.memory_policy["agent_global_memory"]["scope"] == "agent_global"
        assert profile.memory_policy["agent_global_memory"]["compact_threshold"] == 789
        assert profile.memory_policy["agent_global_memory"]["schema"] == [
            "facts",
            "decisions",
            "open_questions",
            "next_actions",
            "risk_flags",
            "evidence_refs",
            "confidence",
        ]
