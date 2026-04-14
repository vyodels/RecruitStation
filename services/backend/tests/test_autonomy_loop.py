import time

from fastapi.testclient import TestClient

from recruit_agent.core.app import create_app
from recruit_agent.core.settings import AppSettings, FeatureFlags
from recruit_agent.models import Candidate, Workflow


def test_autonomy_loop_disabled_by_default(tmp_path):
    app = create_app(
        AppSettings(
            data_dir=str(tmp_path / "data"),
            database_url=f"sqlite:///{tmp_path / 'recruit-agent.db'}",
        )
    )

    with TestClient(app) as client:
        autonomy = client.app.state.autonomy_loop
        assert autonomy.enabled is False
        assert autonomy.is_running() is False


def test_autonomy_loop_processes_enqueued_task_when_enabled(tmp_path):
    app = create_app(
        AppSettings(
            data_dir=str(tmp_path / "data"),
            database_url=f"sqlite:///{tmp_path / 'recruit-agent.db'}",
            feature_flags=FeatureFlags(enable_autonomy=True),
        )
    )
    container = app.state.bootstrap_container
    with container.session_factory() as session:
        candidate = Candidate(
            name="Autonomy Candidate",
            platform="boss",
            platform_candidate_id="boss_autonomy_001",
            status="screening",
        )
        workflow = Workflow(
            name="One Step Workflow",
            status="active",
            config={
                "start_node_id": "initial_screening",
                "nodes": [
                    {
                        "id": "initial_screening",
                        "name": "Initial Screening",
                        "task_type": "initial_screening",
                    }
                ],
            },
        )
        session.add_all([candidate, workflow])
        session.commit()
        session.refresh(candidate)
        session.refresh(workflow)

    container.agent_control.enqueue_task(
        "initial_screening",
        candidate_id=candidate.id,
        workflow_id=workflow.id,
        workflow_node_id="initial_screening",
        payload={"jd_criteria": "Python"},
        priority=250,
    )

    with TestClient(app) as client:
        autonomy = client.app.state.autonomy_loop
        assert autonomy.enabled is True
        assert autonomy.is_running() is True

        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if container.scheduler.history and client.get("/api/agent").json()["queueDepth"] == 0:
                break
            time.sleep(0.05)

        assert container.scheduler.history
        assert container.scheduler.history[0].result.status == "completed"
        assert client.get("/api/agent").json()["queueDepth"] == 0

    assert app.state.autonomy_loop.is_running() is False
