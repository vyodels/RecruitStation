from fastapi.testclient import TestClient

from recruit_agent.core.app import create_app
from recruit_agent.core.settings import AppSettings


def test_health_endpoint_reports_ready(tmp_path):
    app = create_app(
        AppSettings(
            data_dir=str(tmp_path / "data"),
            database_url=f"sqlite:///{tmp_path / 'recruit-agent.db'}",
        )
    )

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}

