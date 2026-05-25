from __future__ import annotations

import pytest

from recruit_station.core.settings import AppSettings
from recruit_station.models.domain import Candidate, CandidateApplication, PersonResumeArtifact, ResumeArtifact
from recruit_station.plugins.recruit.toolkit import (
    archive_candidate,
    attach_resume_artifact,
    create_candidate_review_decision,
    create_candidate_sync_record,
    delete_candidate,
    get_candidate_thread,
    get_jd_progress,
    extract_resume_artifact_text,
    list_candidates,
    list_pending_candidate_message_syncs,
    record_candidate_message,
    record_candidate_message_sync_ack,
    record_outbound_message,
    score_candidate,
    transition_application,
    upsert_candidate,
    upsert_job_description,
)
from recruit_station.services.container import AppContainer


def _build_container(tmp_path) -> AppContainer:
    settings = AppSettings(
        data_dir=str(tmp_path / "data"),
        database_url=f"sqlite:///{tmp_path / 'recruit-candidate-tools.db'}",
        provider_config={},
    )
    return AppContainer.build(settings)


def test_candidate_lifecycle_tools_cover_writeback_scoring_thread_and_progress(tmp_path) -> None:
    container = _build_container(tmp_path)
    for tool_name in (
        "list_candidates",
        "upsert_candidate",
        "score_candidate",
        "record_outbound_message",
        "record_candidate_message",
        "list_pending_candidate_message_syncs",
        "record_candidate_message_sync_ack",
        "attach_resume_artifact",
        "extract_resume_artifact_text",
        "create_candidate_review_decision",
        "create_candidate_sync_record",
        "get_candidate_thread",
        "get_jd_progress",
        "request_human_approval",
    ):
        assert tool_name in container.tool_registry.tools

    job = upsert_job_description(
        container.session_factory,
        title="国际销售工程师",
        platform="boss_mock",
        external_id="job-ai-sales-001",
        description="海外销售与售前协同",
    )["job_description"]

    candidate_result = upsert_candidate(
        container.session_factory,
        name="赵云龙",
        platform="boss_mock",
        platform_candidate_id="geek-zhao-yunlong-001",
        job_description_id=job["job_description_id"],
        current_status="discovered",
        source_observation={
            "viewed_count": 12,
            "communicated_count": 3,
            "interested_count": 1,
            "latest_status": "已看过",
        },
        online_resume_text="德国售前经理，英语沟通，海外项目推进。",
    )
    application = candidate_result["application"]
    assert application is not None
    assert application["source_observation"]["viewed_count"] == 12

    listed = list_candidates(
        container.session_factory,
        job_description_id=job["job_description_id"],
    )
    assert len(listed) == 1
    assert listed[0]["applications"][0]["source_observation"]["communicated_count"] == 3

    scoring = score_candidate(
        container.session_factory,
        application_id=application["application_id"],
        score=90,
        decision="advance",
        summary="海外销售与英语沟通经验匹配，建议推进。",
        dimension_scores={"english": 92, "solution_selling": 88},
        evidence_refs=["德国售前经理", "海外项目"],
    )
    assert scoring["application"]["ai_scores"]["overall"] == 90

    record_outbound_message(
        container.session_factory,
        application_id=application["application_id"],
        content="您好，方便补充联系方式和离线简历吗？",
        channel_hint="boss_chat",
        status="draft",
    )
    record_candidate_message(
        container.session_factory,
        application_id=application["application_id"],
        direction="outbound",
        content="平台侧已存在的一条招聘方消息，不应再次进入本地待同步队列。",
        channel_hint="boss_chat",
        status="sent",
        observed_at="2026-05-11T10:00:30+00:00",
        metadata={"source_event_id": "im-002"},
    )
    record_candidate_message(
        container.session_factory,
        application_id=application["application_id"],
        direction="inbound",
        content="可以，我稍后发 PDF 简历，也可以加微信沟通。",
        channel_hint="boss_chat",
        status="received",
        observed_at="2026-05-11T10:01:00+00:00",
        metadata={"source_event_id": "im-001"},
    )
    pending_syncs = list_pending_candidate_message_syncs(
        container.session_factory,
        application_id=application["application_id"],
        destination="boss_mock_chat",
    )
    assert len(pending_syncs) == 1
    assert pending_syncs[0]["metadata"]["outbound_sync"]["status"] == "pending"
    acked_message = record_candidate_message_sync_ack(
        container.session_factory,
        message_id=pending_syncs[0]["message_id"],
        destination="boss_mock_chat",
        status="synced",
        external_message_id="boss-msg-001",
        external_event_id="boss-event-001",
        observed_at="2026-05-11T10:01:00+00:00",
        metadata={"source_feed": "mock_recruiting_site"},
    )
    assert acked_message["metadata"]["outbound_sync"]["status"] == "synced"
    assert (
        acked_message["metadata"]["outbound_sync"]["destinations"]["boss_mock_chat"]["external_message_id"]
        == "boss-msg-001"
    )
    assert (
        list_pending_candidate_message_syncs(
            container.session_factory,
            application_id=application["application_id"],
            destination="boss_mock_chat",
        )
        == []
    )

    attach_resume_artifact(
        container.session_factory,
        application_id=application["application_id"],
        file_name="zhao-yunlong-resume.pdf",
        file_path="/tmp/zhao-yunlong-resume.pdf",
        extracted_text="离线简历：德国售前经理，海外销售解决方案经验。",
        contact_snapshot={"phone": "13800138000", "email": "zhao@example.com"},
    )

    create_candidate_review_decision(
        container.session_factory,
        application_id=application["application_id"],
        decision="proceed",
        rationale="评分达标且联系信息已补齐。",
        decision_source="agent",
    )

    create_candidate_sync_record(
        container.session_factory,
        application_id=application["application_id"],
        destination="talent_pool",
        status="synced",
        external_ref="pool-001",
        payload_snapshot={"candidate": "赵云龙"},
    )

    thread = get_candidate_thread(
        container.session_factory,
        application_id=application["application_id"],
    )
    assert len(thread["communicationLogs"]) == 3
    assert any(item["direction"] == "inbound" for item in thread["communicationLogs"])
    assert thread["stateSnapshot"]["contact_status"] == "replied"
    assert len(thread["assessments"]) == 1
    assert len(thread["resumeArtifacts"]) == 1
    assert len(thread["reviewDecisions"]) == 2
    assert len(thread["syncRecords"]) == 1
    assert thread["application"]["resumeAvailable"] is True
    assert thread["stateSnapshot"]["resume_status"] == "received"
    with container.session_factory() as session:
        assert session.query(ResumeArtifact).count() == 1
        assert session.query(PersonResumeArtifact).count() == 1
        person_artifact = session.query(PersonResumeArtifact).one()
        assert person_artifact.file_name == "zhao-yunlong-resume.pdf"
        assert person_artifact.file_path == "/tmp/zhao-yunlong-resume.pdf"

    progress = get_jd_progress(
        container.session_factory,
        job_description_id=job["job_description_id"],
    )
    assert progress["candidate_count"] == 1
    assert progress["with_contact"] == 1
    assert progress["with_resume"] == 1
    assert progress["with_ai_score"] == 1


def test_existing_platform_resume_can_transition_from_resume_fetching(tmp_path) -> None:
    container = _build_container(tmp_path)
    job = upsert_job_description(
        container.session_factory,
        title="国际销售工程师",
        platform="boss_mock",
        external_id="job-ai-sales-002",
        description="海外销售与售前协同",
    )["job_description"]
    candidate_result = upsert_candidate(
        container.session_factory,
        name="李青",
        platform="boss_mock",
        platform_candidate_id="geek-li-qing-001",
        job_description_id=job["job_description_id"],
        current_status="offline_resume_fetching",
    )
    application = candidate_result["application"]

    attached = attach_resume_artifact(
        container.session_factory,
        application_id=application["application_id"],
        file_name="li-qing-resume.pdf",
        file_path="/tmp/li-qing-resume.pdf",
        extracted_text="平台侧已存在的简历 artifact。",
    )

    assert "offline_resume_acquired" in [
        str(item.get("toStatus"))
        for item in attached["thread"]["availableTransitions"]
    ]
    assert attached["thread"]["stateSnapshot"]["next_recommended_stages"] == ["offline_resume_acquired"]

    transitioned = transition_application(
        container.session_factory,
        application_id=application["application_id"],
        to_status="offline_resume_acquired",
        stage_key="offline_resume_acquired",
        note="平台侧已有简历，已完成 artifact 入库。",
        trigger="artifact_attached",
    )

    assert transitioned["thread"]["application"]["currentStatus"] == "offline_resume_acquired"
    assert transitioned["thread"]["stateSnapshot"]["current_stage_key"] == "offline_resume_acquired"


def test_extract_resume_artifact_text_runs_on_demand_for_scoring(tmp_path) -> None:
    container = _build_container(tmp_path)
    job = upsert_job_description(container.session_factory, title="AI Agent 产品经理")["job_description"]
    candidate_result = upsert_candidate(
        container.session_factory,
        name="离线简历候选人",
        platform="mock-zhipin",
        platform_candidate_id="cand-offline-resume-001",
        job_description_id=job["job_description_id"],
        current_status="offline_resume_fetching",
    )
    resume_path = tmp_path / "offline-resume.txt"
    resume_path.write_text("离线简历：29岁，本科，5年AI产品经验。", encoding="utf-8")

    attached = attach_resume_artifact(
        container.session_factory,
        application_id=candidate_result["application"]["application_id"],
        file_name="offline-resume.txt",
        file_path=str(resume_path),
    )

    assert attached["artifact"]["extractedText"] is None
    extracted = extract_resume_artifact_text(
        container.session_factory,
        application_id=candidate_result["application"]["application_id"],
        artifact_id=attached["artifact"]["id"],
    )

    assert extracted["artifact"]["extractedText"] == "离线简历：29岁，本科，5年AI产品经验。"
    assert extracted["artifact"]["artifactMetadata"]["text_extraction"]["status"] == "completed"
    assert extracted["thread"]["application"]["resumeSnapshot"]["offline_resume"]["raw_text"] == "离线简历：29岁，本科，5年AI产品经验。"
    assert extracted["thread"]["application"]["resumeSnapshot"]["structured_facts"]["age"] == 29


def test_upsert_candidate_canonicalizes_platform_aliases_for_dedupe(tmp_path) -> None:
    container = _build_container(tmp_path)
    job = upsert_job_description(
        container.session_factory,
        title="交易策略产品经理",
        platform="zhipin",
        external_id="job-strategy-pm-001",
    )["job_description"]

    first_result = upsert_candidate(
        container.session_factory,
        name="金行",
        platform="zhipin",
        platform_candidate_id="金行",
        job_description_id=job["job_description_id"],
        current_status="discovered",
    )
    second_result = upsert_candidate(
        container.session_factory,
        name="金行",
        platform="boss直聘",
        source_platform="BOSS 直聘",
        platform_candidate_id="金行",
        job_description_id=job["job_description_id"],
        current_status="human_screening",
    )

    assert second_result["action"] == "updated"
    assert second_result["application_action"] == "updated"
    assert second_result["candidate"]["candidate_person_id"] == first_result["candidate"]["candidate_person_id"]
    assert second_result["candidate"]["platform"] == "zhipin"
    assert second_result["application"]["application_id"] == first_result["application"]["application_id"]
    assert second_result["application"]["source_platform"] == "zhipin"
    listed = list_candidates(container.session_factory, platform="boss_zhipin")
    assert [item["candidate_person_id"] for item in listed] == [first_result["candidate"]["candidate_person_id"]]

    with container.session_factory() as session:
        assert session.query(Candidate).count() == 1
        assert session.query(CandidateApplication).count() == 1


def test_upsert_candidate_enforces_runtime_max_new_candidates(tmp_path) -> None:
    container = _build_container(tmp_path)
    job = upsert_job_description(container.session_factory, title="交易策略产品经理")["job_description"]
    runtime_constraints = {"max_new_candidates": 1, "run_created_at": 1}

    first_result = upsert_candidate(
        container.session_factory,
        name="候选人甲",
        platform="zhipin",
        platform_candidate_id="候选人甲",
        job_description_id=job["job_description_id"],
        _runtime_constraints=runtime_constraints,
    )

    assert first_result["action"] == "created"
    with pytest.raises(ValueError, match="max_new_candidates=1 reached"):
        upsert_candidate(
            container.session_factory,
            name="候选人乙",
            platform="zhipin",
            platform_candidate_id="候选人乙",
            job_description_id=job["job_description_id"],
            _runtime_constraints=runtime_constraints,
        )

    with container.session_factory() as session:
        assert session.query(Candidate).count() == 1
        assert session.query(CandidateApplication).count() == 1


def test_upsert_candidate_rejects_out_of_scope_job_description_in_scoped_run(tmp_path) -> None:
    container = _build_container(tmp_path)
    in_scope_job = upsert_job_description(container.session_factory, title="AI Agent 产品经理")["job_description"]
    out_of_scope_job = upsert_job_description(container.session_factory, title="国际销售工程师")["job_description"]
    runtime_constraints = {"selected_job_description_ids": [in_scope_job["job_description_id"]]}

    with pytest.raises(ValueError, match="outside current run JD scope"):
        upsert_candidate(
            container.session_factory,
            name="越界候选人",
            platform="mock-zhipin",
            platform_candidate_id="cand-out-of-scope",
            job_description_id=out_of_scope_job["job_description_id"],
            _runtime_constraints=runtime_constraints,
        )

    with pytest.raises(ValueError, match="job_description_id is required"):
        upsert_candidate(
            container.session_factory,
            name="无岗位候选人",
            platform="mock-zhipin",
            platform_candidate_id="cand-without-jd",
            _runtime_constraints=runtime_constraints,
        )

    with container.session_factory() as session:
        assert session.query(Candidate).count() == 0
        assert session.query(CandidateApplication).count() == 0


def test_application_id_only_candidate_tools_reject_out_of_scope_applications(tmp_path) -> None:
    container = _build_container(tmp_path)
    in_scope_job = upsert_job_description(container.session_factory, title="AI Agent 产品经理")["job_description"]
    out_of_scope_job = upsert_job_description(container.session_factory, title="国际销售工程师")["job_description"]
    runtime_constraints = {"selected_job_description_ids": [in_scope_job["job_description_id"]]}
    candidate_result = upsert_candidate(
        container.session_factory,
        name="岗位外候选人",
        platform="mock-zhipin",
        platform_candidate_id="cand-outside-application",
        job_description_id=out_of_scope_job["job_description_id"],
    )
    application_id = candidate_result["application"]["application_id"]

    with pytest.raises(ValueError, match="outside current run JD scope"):
        get_candidate_thread(
            container.session_factory,
            application_id=application_id,
            _runtime_constraints=runtime_constraints,
        )

    with pytest.raises(ValueError, match="outside current run JD scope"):
        score_candidate(
            container.session_factory,
            application_id=application_id,
            score=80,
            decision="advance",
            _runtime_constraints=runtime_constraints,
        )


def test_list_candidates_defaults_to_selected_job_description_scope(tmp_path) -> None:
    container = _build_container(tmp_path)
    in_scope_job = upsert_job_description(container.session_factory, title="AI Agent 产品经理")["job_description"]
    out_of_scope_job = upsert_job_description(container.session_factory, title="国际销售工程师")["job_description"]
    runtime_constraints = {"selected_job_description_ids": [in_scope_job["job_description_id"]]}
    in_scope_candidate = upsert_candidate(
        container.session_factory,
        name="岗位内候选人",
        platform="mock-zhipin",
        platform_candidate_id="cand-inside-scope",
        job_description_id=in_scope_job["job_description_id"],
    )
    upsert_candidate(
        container.session_factory,
        name="岗位外候选人",
        platform="mock-zhipin",
        platform_candidate_id="cand-outside-scope",
        job_description_id=out_of_scope_job["job_description_id"],
    )

    listed = list_candidates(container.session_factory, _runtime_constraints=runtime_constraints)

    assert [item["candidate_person_id"] for item in listed] == [
        in_scope_candidate["candidate"]["candidate_person_id"]
    ]
    assert [item["applications"][0]["job_description_id"] for item in listed] == [
        in_scope_job["job_description_id"]
    ]


def test_upsert_candidate_uses_runtime_name_dedupe_hint(tmp_path) -> None:
    container = _build_container(tmp_path)
    job = upsert_job_description(container.session_factory, title="交易策略产品经理")["job_description"]

    first_result = upsert_candidate(
        container.session_factory,
        name="陈**",
        platform="zhipin",
        job_description_id=job["job_description_id"],
    )
    second_result = upsert_candidate(
        container.session_factory,
        name="陈**",
        platform="BOSS直聘",
        platform_candidate_id="陈**",
        job_description_id=job["job_description_id"],
        _runtime_constraints={"dedupe_existing_candidate_names": ["陈**"]},
    )

    assert second_result["action"] == "updated"
    assert second_result["candidate"]["candidate_person_id"] == first_result["candidate"]["candidate_person_id"]
    assert second_result["application"]["application_id"] == first_result["application"]["application_id"]
    with container.session_factory() as session:
        assert session.query(Candidate).count() == 1
        assert session.query(CandidateApplication).count() == 1


def test_upsert_candidate_keeps_page_status_text_out_of_canonical_state(tmp_path) -> None:
    container = _build_container(tmp_path)
    job = upsert_job_description(
        container.session_factory,
        title="国际销售工程师",
        platform="boss_mock",
        external_id="job-ai-sales-003",
        description="海外销售与售前协同",
    )["job_description"]

    candidate_result = upsert_candidate(
        container.session_factory,
        name="李青",
        platform="boss_mock",
        platform_candidate_id="geek-li-qing-002",
        job_description_id=job["job_description_id"],
        current_status="active",
        current_stage_key="初筛中",
    )

    application = candidate_result["application"]
    assert application["current_status"] == "discovered"
    assert application["current_stage_key"] == "discovered"
    assert "online_resume_fetching" in application["state_snapshot"]["next_recommended_stages"]
    assert application["application_metadata"]["source_state"] == {
        "requested_current_status": "active",
        "normalized_current_status": "discovered",
        "requested_current_stage_key": "初筛中",
        "normalized_current_stage_key": "discovered",
    }


def test_upsert_candidate_uses_known_stage_when_page_status_is_display_text(tmp_path) -> None:
    container = _build_container(tmp_path)
    job = upsert_job_description(
        container.session_factory,
        title="国际销售工程师",
        platform="boss_mock",
        external_id="job-ai-sales-004",
        description="海外销售与售前协同",
    )["job_description"]

    candidate_result = upsert_candidate(
        container.session_factory,
        name="王海",
        platform="boss_mock",
        platform_candidate_id="geek-wang-hai-001",
        job_description_id=job["job_description_id"],
        current_status="active",
        current_stage_key="offline_resume_acquired",
    )

    application = candidate_result["application"]
    assert application["current_status"] == "offline_resume_acquired"
    assert application["current_stage_key"] == "offline_resume_acquired"
    assert "offline_resume_passed" in application["state_snapshot"]["next_recommended_stages"]
    assert application["application_metadata"]["source_state"] == {
        "requested_current_status": "active",
        "normalized_current_status": "offline_resume_acquired",
    }


def test_upsert_candidate_extracts_contact_info_from_profile_text(tmp_path) -> None:
    container = _build_container(tmp_path)
    job = upsert_job_description(container.session_factory, title="后端平台工程师")["job_description"]

    candidate_result = upsert_candidate(
        container.session_factory,
        name="赵启明",
        platform="mock-zhipin",
        platform_candidate_id="cand-mock-005",
        job_description_id=job["job_description_id"],
        current_status="online_resume_rejected",
        online_resume_text=(
            "3年PHP后端，CMS和营销页，缺少平台/状态机经验。"
            "联系方式：phone 138-0001-1005；email zhao.qiming@example.com。"
        ),
    )

    candidate = candidate_result["candidate"]
    application = candidate_result["application"]
    assert candidate["contact_info"]["phone"] == "13800011005"
    assert candidate["contact_info"]["email"] == "zhao.qiming@example.com"
    assert candidate["contact_info"]["channels"] == ["phone", "email"]
    assert application["contact_snapshot"]["channels"] == ["phone", "email"]
    assert application["state_snapshot"]["contact_acquired"] is True


def test_upsert_candidate_preserves_full_online_resume_data(tmp_path) -> None:
    container = _build_container(tmp_path)
    job = upsert_job_description(container.session_factory, title="AI Agent 产品经理")["job_description"]
    resume_text = (
        "您好，我对岗位很有兴趣，能进一步沟通吗？\n"
        "本人美团1年AI-agent产品经验，3年商品策略产品。"
    )

    candidate_result = upsert_candidate(
        container.session_factory,
        name="金行",
        platform="mock-zhipin",
        platform_candidate_id="cand-mock-jin-xing",
        job_description_id=job["job_description_id"],
        current_status="replied",
        online_resume_data={
            "rawText": resume_text,
            "source": "communication_online_resume",
            "sections": {
                "introduction": "您好，我对岗位很有兴趣，能进一步沟通吗？",
                "experience": "美团1年AI-agent产品经验，3年商品策略产品",
            },
        },
    )

    candidate = candidate_result["candidate"]
    application = candidate_result["application"]
    assert candidate["online_resume_text"] == resume_text
    assert application["resume_snapshot"]["online_resume"]["raw_text"] == resume_text
    assert application["resume_snapshot"]["online_resume"]["sections"]["experience"] == "美团1年AI-agent产品经验，3年商品策略产品"
    assert application["resume_snapshot"]["online_resume"]["source"] == "communication_online_resume"


def test_candidate_lifecycle_tools_support_archive_and_delete(tmp_path) -> None:
    container = _build_container(tmp_path)
    job = upsert_job_description(container.session_factory, title="销售工程师")["job_description"]
    candidate_result = upsert_candidate(
        container.session_factory,
        name="邹燕琴",
        platform="boss_mock",
        platform_candidate_id="geek-zou-yanqin-001",
        job_description_id=job["job_description_id"],
        current_status="discovered",
    )
    application = candidate_result["application"]

    archived = archive_candidate(
        container.session_factory,
        application_id=application["application_id"],
        note="当前轮次归档验证",
    )
    assert archived["thread"]["application"]["currentStatus"] == "exception_closed"

    deleted = delete_candidate(
        container.session_factory,
        candidate_person_id=candidate_result["candidate"]["candidate_person_id"],
    )
    assert deleted["deleted"] is True
    assert list_candidates(container.session_factory, job_description_id=job["job_description_id"]) == []
