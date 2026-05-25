from __future__ import annotations

import importlib.util
from pathlib import Path

from sqlalchemy import func, select

from recruit_station.core.settings import AppSettings
from recruit_station.db.session import create_engine_from_settings, create_session_factory, initialize_database
from recruit_station.models import AgentDefinition, AppSetting, Candidate, JobDescription, TaskSpec


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "clear_business_data.py"
spec = importlib.util.spec_from_file_location("clear_business_data_script", SCRIPT_PATH)
assert spec is not None and spec.loader is not None
clear_business_data_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(clear_business_data_script)


def _count(session, model) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def test_clear_business_data_preserves_config_and_deletes_business_rows(tmp_path: Path) -> None:
    settings = AppSettings(
        data_dir=str(tmp_path / "data"),
        database_url=f"sqlite:///{tmp_path / 'recruit-station.db'}",
        provider_config={},
    )
    engine = create_engine_from_settings(settings)
    initialize_database(engine)
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        session.add(AppSetting(id="singleton", payload={"theme": "dark"}))
        session.add(AgentDefinition(definition_key="primary", name="Primary Agent", status="active", is_primary=True))
        session.add(JobDescription(title="Real site test JD", source="manual"))
        session.add(Candidate(name="Candidate A", platform="site"))
        session.add(TaskSpec(title="Runtime task", instruction="Observe site."))
        session.commit()

    result = clear_business_data_script.clear_business_data(settings, dry_run=False, vacuum=False)

    assert result["deleted_rows"]["job_descriptions"] == 1
    assert result["deleted_rows"]["candidate_persons"] == 1
    assert result["deleted_rows"]["task_specs"] == 1
    assert "agent_definitions" in result["preserved_tables"]
    assert "app_settings" in result["preserved_tables"]

    with session_factory() as session:
        assert _count(session, AppSetting) == 1
        assert _count(session, AgentDefinition) == 1
        assert _count(session, JobDescription) == 0
        assert _count(session, Candidate) == 0
        assert _count(session, TaskSpec) == 0
