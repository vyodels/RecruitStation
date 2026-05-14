from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from recruit_station.core.settings import AppSettings
from recruit_station.db.session import create_engine_from_settings, create_session_factory, initialize_database
from recruit_station.models.domain import AgentDefinition
from recruit_station.services.recruit_station import ensure_primary_agent_definition


def _make_session(tmp_path: Path) -> Session:
    settings = AppSettings(
        data_dir=str(tmp_path / "data"),
        database_url=f"sqlite:///{tmp_path / 'recruit-station-definition.db'}",
    )
    engine = create_engine_from_settings(settings)
    initialize_database(engine)
    return create_session_factory(engine)()


def test_ensure_primary_agent_definition_normalizes_memory_writeback_policy(tmp_path: Path) -> None:
    session = _make_session(tmp_path)
    try:
        session.add(
            AgentDefinition(
                definition_key="recruit-station",
                name="RecruitStation",
                is_primary=True,
                prompt_config={},
                memory_policy={
                    "legacy_candidate_context": {"schema": ["legacy_business_context"]},
                    "legacy_job_context": {"schema": ["legacy_business_context"]},
                    "legacy_global_context": {"schema": ["legacy_business_context"]},
                    "writeback": {"auto_write_min_confidence": 0.8, "max_stable_facts": 2},
                },
            )
        )
        session.commit()

        definition = ensure_primary_agent_definition(session)

        assert set(definition.memory_policy) == {"writeback"}
        assert definition.memory_policy["writeback"]["auto_write_min_confidence"] == 0.8
        assert definition.memory_policy["writeback"]["max_stable_facts"] == 2
    finally:
        session.close()
