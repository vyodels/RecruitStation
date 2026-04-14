from fastapi.testclient import TestClient

from recruit_agent.core.app import create_app
from recruit_agent.core.settings import AppSettings


def make_client(tmp_path):
    app = create_app(
        AppSettings(
            data_dir=str(tmp_path / "data"),
            database_url=f"sqlite:///{tmp_path / 'recruit-agent.db'}",
        )
    )
    return TestClient(app)


def test_skill_health_check_and_learning_drafts(tmp_path):
    with make_client(tmp_path) as client:
        skill_response = client.post(
            "/api/skills",
            json={
                "skill_id": "resume-health",
                "name": "Resume Health",
                "version": 1,
                "status": "approved",
                "platform": "boss",
                "strategy": {"prompt": "screen"},
                "health_check_config": {"required_strategy_keys": ["prompt", "rubric"]},
            },
        )
        assert skill_response.status_code == 201
        skill_id = skill_response.json()["id"]

        health_response = client.post(
            f"/api/skills/{skill_id}/health-check",
            json={"observed_result": {"status": "pass", "overall": 88}},
        )
        assert health_response.status_code == 200
        assert health_response.json()["health"] == "warning"
        assert "missing_strategy_key:rubric" in health_response.json()["issues"]

        learning_response = client.post(
            "/api/skills/learnings",
            json={
                "content": "Need a better rubric for frontend architecture signals.",
                "tags": ["screening", "boss"],
                "source_task_id": "task-123",
            },
        )
        assert learning_response.status_code == 201
        learning_id = learning_response.json()["id"]
        assert learning_response.json()["is_active"] is True

        list_response = client.get("/api/skills/learnings")
        assert list_response.status_code == 200
        assert any(item["id"] == learning_id for item in list_response.json())

        deactivate_response = client.post(f"/api/skills/learnings/{learning_id}/deactivate")
        assert deactivate_response.status_code == 200
        assert deactivate_response.json()["is_active"] is False

        activate_response = client.post(f"/api/skills/learnings/{learning_id}/activate")
        assert activate_response.status_code == 200
        assert activate_response.json()["is_active"] is True

        dashboard_response = client.get("/api/dashboard")
        assert dashboard_response.status_code == 200
        alert_labels = [item["label"] for item in dashboard_response.json()["alerts"]]
        assert "Learning draft available" in alert_labels
