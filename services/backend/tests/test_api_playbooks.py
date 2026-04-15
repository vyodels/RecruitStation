from fastapi.testclient import TestClient

from scene_pilot.core.app import create_app
from scene_pilot.core.settings import AppSettings

PLAYBOOKS_API_BASE = "/api/recruit-agent/playbooks"


def make_client(tmp_path):
    app = create_app(
        AppSettings(
            data_dir=str(tmp_path / "data"),
            database_url=f"sqlite:///{tmp_path / 'recruit-agent.db'}",
        )
    )
    return TestClient(app)


def test_playbook_crud(tmp_path):
    with make_client(tmp_path) as client:
        create_response = client.post(
            PLAYBOOKS_API_BASE,
            json={
                "name": "Initial Screening",
                "description": "Initial adaptive screening blueprint",
                "scope_kind": "jd",
                "scope_ref": "jd-001",
                "blueprint": {"nodes": ["candidate_discovery", "candidate_probe"]},
                "strategy_defaults": {"entry_stage": "candidate_discovery"},
                "context_overrides": {"candidate_probe": {"prefer": ["candidate_memory"]}},
                "status": "draft",
                "version": 1,
            },
        )
        assert create_response.status_code == 201
        playbook = create_response.json()
        assert playbook["name"] == "Initial Screening"

        playbook_id = playbook["id"]
        list_response = client.get(PLAYBOOKS_API_BASE)
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

        patch_response = client.patch(
            f"{PLAYBOOKS_API_BASE}/{playbook_id}",
            json={"status": "active", "version": 2},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["status"] == "active"
        assert patch_response.json()["version"] == 2

        delete_response = client.delete(f"{PLAYBOOKS_API_BASE}/{playbook_id}")
        assert delete_response.status_code == 204
