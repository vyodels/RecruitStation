from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

from recruit_station.core.settings import load_settings
from recruit_station.repositories.domain import (
    AgentSessionRepository,
    ApprovalRepository,
    CandidateApplicationRepository,
    CandidateRepository,
    JobDescriptionRepository,
    OperatorInteractionRepository,
)
from recruit_station.server import create_app
from recruit_station.services.recruit_station import ensure_primary_agent_definition


def test_resume_artifact_updates_candidate_projection(tmp_path: Path) -> None:
    os.environ["RECRUIT_STATION_DATA_DIR"] = str(tmp_path)
    load_settings.cache_clear()
    resume_path = tmp_path / "alice-resume.txt"
    resume_text = "Alice，29岁，本科，8年以上后端经验，在职。"
    resume_path.write_text(resume_text, encoding="utf-8")
    app = create_app()
    client = TestClient(app)
    client.__enter__()
    try:
        session_factory = app.state.session_factory
        with session_factory() as session:
            candidate = CandidateRepository(session).create(
                {
                    "name": "Alice",
                    "platform": "boss",
                    "platform_candidate_id": "boss-001",
                }
            )
            job = JobDescriptionRepository(session).create({"title": "Backend Engineer"})
            application = CandidateApplicationRepository(session).create(
                {
                    "person_id": candidate.candidate_person_id,
                    "job_description_id": job.job_description_id,
                    "platform": "boss",
                    "source_platform": "boss",
                    "current_status": "discovered",
                }
            )

        created = client.post(
            f"/api/candidate-applications/{application.candidate_application_id}/resume-artifacts",
            json={
                "source": "boss",
                "artifactType": "resume",
                "fileName": "alice-resume.txt",
                "filePath": str(resume_path),
                "contactSnapshot": {
                    "phone": "13800138000",
                    "email": "alice@example.com",
                },
                "artifactMetadata": {
                    "source": "boss",
                    "channel": "resume_download",
                },
            },
        )
        assert created.status_code == 201

        application_read = client.get(f"/api/candidate-applications/{application.candidate_application_id}")
        assert application_read.status_code == 200
        payload = application_read.json()
        assert payload["resumeAvailable"] is True
        assert payload["contactInfo"]["phone"] == "13800138000"
        assert payload["resumePath"] == str(resume_path)
        assert payload["onlineResumeText"] is None
        assert payload["contactSnapshot"]["phone"] == "13800138000"
        assert payload["resumeSnapshot"]["file_path"] == str(resume_path)
        assert payload["resumeSnapshot"]["offline_resume"]["file_path"] == str(resume_path)
        assert "raw_text" not in payload["resumeSnapshot"]["offline_resume"]

        artifact_id = created.json()["id"]
        preview = client.get(
            f"/api/candidate-applications/{application.candidate_application_id}/resume-artifacts/{artifact_id}/preview"
        )
        assert preview.status_code == 200
        assert preview.content.decode("utf-8") == resume_text

        extracted = client.post(
            f"/api/candidate-applications/{application.candidate_application_id}/resume-artifacts/{artifact_id}/extract-text"
        )
        assert extracted.status_code == 200
        extracted_payload = extracted.json()
        assert extracted_payload["extractedText"] == resume_text
        assert extracted_payload["artifactMetadata"]["text_extraction"]["status"] == "completed"

        application_read_after_extract = client.get(f"/api/candidate-applications/{application.candidate_application_id}")
        assert application_read_after_extract.status_code == 200
        payload_after_extract = application_read_after_extract.json()
        assert payload_after_extract["onlineResumeText"] is None
        assert payload_after_extract["resumeSnapshot"]["offline_resume"]["raw_text"] == resume_text
        assert payload_after_extract["resumeSnapshot"]["structured_facts"]["age"] == 29
        assert payload_after_extract["resumeSnapshot"]["structured_facts"]["education"] == "本科"
        assert payload_after_extract["resumeSnapshot"]["structured_facts"]["experience_years"] == 8

        thread = client.get(f"/api/candidate-applications/{application.candidate_application_id}/thread")
        assert thread.status_code == 200
        thread_payload = thread.json()
        assert thread_payload["application"]["resumeAvailable"] is True
        assert thread_payload["application"]["person"]["resumePath"] == str(resume_path)
        assert thread_payload["application"]["person"]["onlineResumeText"] is None
        assert thread_payload["application"]["contactSnapshot"]["email"] == "alice@example.com"
        assert thread_payload["application"]["resumeSnapshot"]["status"] == "received"
        assert len(thread_payload["resumeArtifacts"]) == 1
        assert thread_payload["resumeArtifacts"][0]["extractedText"] == resume_text
    finally:
        client.__exit__(None, None, None)
        os.environ.pop("RECRUIT_STATION_DATA_DIR", None)
        load_settings.cache_clear()


def test_application_thread_runtime_records_are_isolated_by_application_id(tmp_path: Path) -> None:
    os.environ["RECRUIT_STATION_DATA_DIR"] = str(tmp_path)
    load_settings.cache_clear()
    app = create_app()
    client = TestClient(app)
    client.__enter__()
    try:
        session_factory = app.state.session_factory
        with session_factory() as session:
            candidate = CandidateRepository(session).create(
                {
                    "name": "Bob",
                    "platform": "boss",
                    "platform_candidate_id": "boss-002",
                }
            )
            job = JobDescriptionRepository(session).create({"title": "Staff Engineer"})
            other_job = JobDescriptionRepository(session).create({"title": "Principal Engineer"})
            application_a = CandidateApplicationRepository(session).create(
                {
                    "person_id": candidate.candidate_person_id,
                    "job_description_id": job.job_description_id,
                    "platform": "boss",
                    "source_platform": "boss",
                    "current_status": "discovered",
                }
            )
            application_b = CandidateApplicationRepository(session).create(
                {
                    "person_id": candidate.candidate_person_id,
                    "job_description_id": other_job.job_description_id,
                    "platform": "boss",
                    "source_platform": "boss",
                    "current_status": "contacting",
                }
            )
            definition = ensure_primary_agent_definition(session)
            runtime_session = AgentSessionRepository(session).create(
                {
                    "agent_definition_id": definition.id,
                    "session_key": "primary",
                    "status": "active",
                    "runtime_metadata": {"definition_key": definition.definition_key},
                }
            )

            approval_a = ApprovalRepository(session).create(
                {
                    "target_type": "candidate_application",
                    "target_id": application_a.id,
                    "title": "Approve application A outreach",
                    "payload": {"application_id": application_a.candidate_application_id},
                }
            )
            approval_b = ApprovalRepository(session).create(
                {
                    "target_type": "candidate_application",
                    "target_id": application_b.candidate_application_id,
                    "title": "Approve application B outreach",
                    "payload": {"application_id": application_b.candidate_application_id},
                }
            )
            ApprovalRepository(session).create(
                {
                    "target_type": "candidate_person",
                    "target_id": candidate.candidate_person_id,
                    "title": "Generic person approval",
                    "payload": {"candidate_id": candidate.candidate_person_id},
                }
            )

            OperatorInteractionRepository(session).create(
                {
                    "session_id": runtime_session.id,
                    "person_id": candidate.candidate_person_id,
                    "application_id": application_a.candidate_application_id,
                    "approval_id": approval_a.id,
                    "title": "Resolve application A approval",
                    "agent_prompt": "只处理 application A",
                    "interaction_type": "confirm",
                    "interaction_metadata": {},
                }
            )
            OperatorInteractionRepository(session).create(
                {
                    "session_id": runtime_session.id,
                    "person_id": candidate.candidate_person_id,
                    "application_id": application_b.candidate_application_id,
                    "approval_id": approval_b.id,
                    "title": "Resolve application B approval",
                    "agent_prompt": "只处理 application B",
                    "interaction_type": "confirm",
                    "interaction_metadata": {},
                }
            )
            OperatorInteractionRepository(session).create(
                {
                    "session_id": runtime_session.id,
                    "person_id": candidate.candidate_person_id,
                    "application_id": application_a.candidate_application_id,
                    "title": "Application A direct interaction",
                    "agent_prompt": "metadata points to application A",
                    "interaction_type": "confirm",
                    "interaction_metadata": {"application_id": application_a.candidate_application_id},
                }
            )
            OperatorInteractionRepository(session).create(
                {
                    "session_id": runtime_session.id,
                    "person_id": candidate.candidate_person_id,
                    "title": "Generic person interaction",
                    "agent_prompt": "person-level only",
                    "interaction_type": "confirm",
                    "interaction_metadata": {},
                }
            )

        thread = client.get(f"/api/candidate-applications/{application_a.candidate_application_id}/thread")
        assert thread.status_code == 200
        payload = thread.json()

        assert [item["title"] for item in payload["runtimeApprovals"]] == ["Approve application A outreach"]
        assert {item["title"] for item in payload["runtimeInteractions"]} == {
            "Resolve application A approval",
            "Application A direct interaction",
        }
    finally:
        client.__exit__(None, None, None)
        os.environ.pop("RECRUIT_STATION_DATA_DIR", None)
        load_settings.cache_clear()
