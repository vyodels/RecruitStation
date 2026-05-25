from __future__ import annotations

import pytest
from sqlalchemy import func, select

from recruit_station.core.settings import AppSettings
from recruit_station.models.domain import Candidate, CandidateApplication
from recruit_station.plugins.recruit.toolkit import list_job_descriptions, upsert_job_description
from recruit_station.services.container import AppContainer


def _build_container(tmp_path) -> AppContainer:
    settings = AppSettings(
        data_dir=str(tmp_path / "data"),
        database_url=f"sqlite:///{tmp_path / 'recruit-job-tools.db'}",
        provider_config={},
    )
    return AppContainer.build(settings)


def test_upsert_job_description_creates_and_updates_same_platform_identity(tmp_path) -> None:
    container = _build_container(tmp_path)
    assert "list_job_descriptions" in container.tool_registry.tools
    assert "upsert_job_description" in container.tool_registry.tools
    tool = container.tool_registry.tools["upsert_job_description"]
    assert {"company_name", "employment_type", "experience_requirement", "education_requirement"} <= set(
        tool.parameters["properties"]
    )
    assert {"compensation_text", "summary", "benefit_tags", "detail_metadata"} <= set(tool.parameters["properties"])
    assert "list-only" in tool.description
    assert "detail_complete=true" in tool.parameters["properties"]["sync_metadata"]["description"]

    created = upsert_job_description(
        container.session_factory,
        title="Backend Engineer",
        company_name="RecruitStation",
        department="Platform",
        location="Shanghai",
        employment_type="full_time",
        compensation_text="30k-45k x 14",
        experience_requirement="5+ years in backend or platform engineering.",
        education_requirement="Bachelor degree or above.",
        summary="Own the backend foundation for recruiting workflows.",
        platform="generic_recruiting_site",
        external_id="job-001",
        external_url="https://example.test/jobs/001",
        description="Build agent runtime services.",
        requirements="Strong Python and distributed systems fundamentals.",
        benefit_tags=["Lunch", "Remote-friendly", "Lunch"],
        detail_metadata={"language": "zh-CN", "team_size": "12"},
        sync_metadata={"detail_sync": "full"},
    )

    updated = upsert_job_description(
        container.session_factory,
        title="Backend Engineer",
        platform="generic_recruiting_site",
        external_id="job-001",
        summary="Own the backend foundation for recruiting and agent workflows.",
        description="Build agent runtime services and APIs.",
    )

    assert created["action"] == "created"
    assert updated["action"] == "updated"
    assert created["job_description"]["job_description_id"] == updated["job_description"]["job_description_id"]
    assert updated["job_description"]["company_name"] == "RecruitStation"
    assert updated["job_description"]["employment_type"] == "full_time"
    assert updated["job_description"]["compensation_text"] == "30k-45k x 14"
    assert updated["job_description"]["experience_requirement"] == "5+ years in backend or platform engineering."
    assert updated["job_description"]["education_requirement"] == "Bachelor degree or above."
    assert updated["job_description"]["benefit_tags"] == ["Lunch", "Remote-friendly"]
    assert updated["job_description"]["detail_metadata"] == {"language": "zh-CN", "team_size": "12"}
    assert updated["job_description"]["summary"] == "Own the backend foundation for recruiting and agent workflows."
    assert updated["job_description"]["description"] == "Build agent runtime services and APIs."
    assert updated["platform_identity"]["sync_metadata"] == {"detail_sync": "full"}

    listed = list_job_descriptions(container.session_factory)
    assert len(listed) == 1
    assert listed[0]["title"] == "Backend Engineer"
    assert listed[0]["platform_identities"][0]["external_id"] == "job-001"
    assert listed[0]["platform_identities"][0]["sync_metadata"] == {"detail_sync": "full"}


def test_upsert_job_description_reuses_matching_external_id_across_platforms(tmp_path) -> None:
    container = _build_container(tmp_path)

    created = upsert_job_description(
        container.session_factory,
        title="International Sales Engineer",
        department="Sales",
        platform="target_site",
        external_id="jd-sales-001",
        external_url="http://127.0.0.1:5179/jobs/jd-sales-001",
    )
    updated = upsert_job_description(
        container.session_factory,
        title="International Sales Engineer",
        department="Sales",
        location="Shanghai",
        platform="mock_recruiting_site",
        external_id="jd-sales-001",
        external_url="http://127.0.0.1:5179/jobs/jd-sales-001",
        summary="Current mock fixture detail page has been read.",
    )

    assert updated["action"] == "updated"
    assert created["job_description"]["job_description_id"] == updated["job_description"]["job_description_id"]

    listed = list_job_descriptions(container.session_factory)
    assert len(listed) == 1
    assert listed[0]["location"] == "Shanghai"
    assert {identity["platform"] for identity in listed[0]["platform_identities"]} == {
        "mock_recruiting_site",
        "target_site",
    }


def test_upsert_job_description_title_fallback_allows_missing_existing_location(tmp_path) -> None:
    container = _build_container(tmp_path)

    created = upsert_job_description(
        container.session_factory,
        title="Data Product Manager",
        department="Product",
        platform="legacy_site",
        external_id="jd-pm-004",
        external_url="http://127.0.0.1:5179/jobs/jd-pm-004",
    )
    updated = upsert_job_description(
        container.session_factory,
        title="Data Product Manager",
        department="Product",
        location="Hangzhou",
        platform="mock_recruiting_site",
        external_id="jd-pm-004-copy",
        external_url="http://127.0.0.1:5179/jobs/jd-pm-004",
    )

    assert updated["action"] == "updated"
    assert created["job_description"]["job_description_id"] == updated["job_description"]["job_description_id"]
    assert len(list_job_descriptions(container.session_factory)) == 1


def test_mock_jd_sync_rejects_fields_that_do_not_match_sync_json(tmp_path, monkeypatch) -> None:
    container = _build_container(tmp_path)
    monkeypatch.setattr(
        "recruit_station.plugins.recruit.toolkit.urlopen",
        lambda *_args, **_kwargs: _FakeUrlResponse(
            """
            <html><body>
              <pre class="sync-json">{
                &quot;external_id&quot;: &quot;jd-pm-004&quot;,
                &quot;title&quot;: &quot;数据产品经理&quot;,
                &quot;company_name&quot;: &quot;星瀚智能制造&quot;,
                &quot;department&quot;: &quot;数据产品部&quot;,
                &quot;location&quot;: &quot;杭州&quot;,
                &quot;compensation_text&quot;: &quot;28k-45k · 14薪&quot;,
                &quot;headcount&quot;: 1,
                &quot;external_url_path&quot;: &quot;/jobs/jd-pm-004&quot;
              }</pre>
            </body></html>
            """,
        ),
    )

    with pytest.raises(ValueError, match="department.*数据产品部"):
        upsert_job_description(
            container.session_factory,
            title="数据产品经理",
            company_name="星瀚智能制造",
            department="产品部",
            location="杭州",
            compensation_text="28k-45k · 14薪",
            headcount=1,
            platform="mock_recruiting_site",
            external_id="jd-pm-004",
            external_url="http://127.0.0.1:5179/jobs/jd-pm-004",
            sync_metadata={
                "detail_complete": True,
                "observed_detail_url": "http://127.0.0.1:5179/jobs/jd-pm-004",
                "blockers": [],
                "missing_fields": [],
            },
        )

    assert list_job_descriptions(container.session_factory) == []


def test_mock_jd_sync_accepts_fields_that_match_sync_json(tmp_path, monkeypatch) -> None:
    container = _build_container(tmp_path)
    monkeypatch.setattr(
        "recruit_station.plugins.recruit.toolkit.urlopen",
        lambda *_args, **_kwargs: _FakeUrlResponse(
            """
            <pre class="sync-json">{
              &quot;external_id&quot;: &quot;jd-solution-002&quot;,
              &quot;title&quot;: &quot;解决方案顾问&quot;,
              &quot;company_name&quot;: &quot;星瀚智能制造&quot;,
              &quot;department&quot;: &quot;售前咨询部&quot;,
              &quot;location&quot;: &quot;北京&quot;,
              &quot;compensation_text&quot;: &quot;30k-48k · 13薪&quot;,
              &quot;headcount&quot;: 2,
              &quot;external_url_path&quot;: &quot;/jobs/jd-solution-002&quot;
            }</pre>
            """,
        ),
    )

    stored = upsert_job_description(
        container.session_factory,
        title="解决方案顾问",
        company_name="星瀚智能制造",
        department="售前咨询部",
        location="北京",
        compensation_text="30k-48k · 13薪",
        headcount=2,
        platform="mock_recruiting_site",
        external_id="jd-solution-002",
        external_url="http://127.0.0.1:5179/jobs/jd-solution-002",
        sync_metadata={
            "detail_complete": True,
            "observed_detail_url": "http://127.0.0.1:5179/jobs/jd-solution-002",
            "blockers": [],
            "missing_fields": [],
        },
    )

    assert stored["action"] == "created"
    assert stored["job_description"]["department"] == "售前咨询部"


def test_jd_sync_upsert_rejects_historical_memory_evidence(tmp_path) -> None:
    container = _build_container(tmp_path)

    with pytest.raises(ValueError, match="current-run page evidence"):
        upsert_job_description(
            container.session_factory,
            title="交易策略产品经理",
            platform="boss_zhipin",
            external_id="jd-001",
            external_url="https://www.zhipin.com/web/geek/job?encryptId=jd-001",
            description="岗位职责已读取。",
            requirements="任职要求已读取。",
            detail_metadata={
                "observed_from_memory_run": "019e51059531710c873f5540254699b5",
                "source_note": "基于已存在本地JD id进行事实性更新写回。",
            },
            sync_metadata={"detail_complete": True},
            _runtime_constraints={"plan_kind": "jd_sync"},
        )

    assert list_job_descriptions(container.session_factory) == []


def test_jd_sync_upsert_rejects_new_or_draft_job_url(tmp_path) -> None:
    container = _build_container(tmp_path)

    with pytest.raises(ValueError, match="not a new or draft job form"):
        upsert_job_description(
            container.session_factory,
            title="交易策略产品经理",
            platform="boss_zhipin",
            external_id="0",
            external_url="https://www.zhipin.com/web/chat/job/edit?encryptId=0&enterSource=2",
            description="岗位职责已读取。",
            requirements="任职要求已读取。",
            sync_metadata={
                "detail_complete": True,
                "observed_detail_url": "https://www.zhipin.com/web/chat/job/edit?encryptId=0&enterSource=2",
            },
            _runtime_constraints={"plan_kind": "jd_sync"},
        )

    assert list_job_descriptions(container.session_factory) == []


def test_jd_sync_upsert_rejects_placeholder_detail_assertions_without_candidate_writes(tmp_path) -> None:
    container = _build_container(tmp_path)

    with pytest.raises(ValueError, match="concrete page-derived responsibilities"):
        upsert_job_description(
            container.session_factory,
            title="产品实习生",
            location="北京",
            employment_type="全职",
            status="active",
            source="jd_sync",
            platform="boss_zhipin",
            external_id="boss-product-intern-001",
            external_url="https://www.zhipin.com/web/geek/job?encryptId=boss-product-intern-001",
            description="岗位职责、任职要求、地点、部门等完整职位详情已在 scene 证据中确认可见。",
            requirements="完整任职要求已在职位详情页中确认可见。",
            sync_metadata={
                "detail_complete": True,
                "observed_detail_url": "https://www.zhipin.com/web/geek/job?encryptId=boss-product-intern-001",
                "blockers": [],
                "missing_fields": [],
            },
            _runtime_constraints={"plan_kind": "jd_sync"},
        )

    assert list_job_descriptions(container.session_factory) == []
    with container.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Candidate)) == 0
        assert session.scalar(select(func.count()).select_from(CandidateApplication)) == 0


def test_jd_sync_upsert_rejects_list_only_placeholder_before_db_write(tmp_path) -> None:
    container = _build_container(tmp_path)

    with pytest.raises(ValueError, match="list-only placeholder"):
        upsert_job_description(
            container.session_factory,
            title="BOSS直聘开放中职位",
            company_name="未知",
            location="未知",
            summary="来自 zhipin.com 职位管理 / 开放中 列表，详情待继续读取。",
            status="active",
            source="jd_sync",
            platform="boss_zhipin",
            external_id="https://www.zhipin.com/web/chat/job/list?ka=menu-manager-job",
            external_url="https://www.zhipin.com/web/chat/job/list?ka=menu-manager-job",
            sync_status="partial",
            description="负责从职位管理开放中列表继续识别职位详情并补充职责信息。",
            requirements="要求继续进入详情页读取岗位要求后再完成同步。",
            sync_metadata={
                "detail_complete": False,
                "observed_detail_url": "https://www.zhipin.com/web/chat/job/list?ka=menu-manager-job",
                "blockers": [],
                "missing_fields": ["job_detail_text"],
            },
            _runtime_constraints={"plan_kind": "jd_sync"},
        )

    assert list_job_descriptions(container.session_factory) == []


def test_jd_sync_upsert_accepts_concrete_page_detail_text(tmp_path) -> None:
    container = _build_container(tmp_path)

    stored = upsert_job_description(
        container.session_factory,
        title="产品实习生",
        location="北京",
        employment_type="全职",
        status="active",
        source="jd_sync",
        platform="boss_zhipin",
        external_id="boss-product-intern-002",
        external_url="https://www.zhipin.com/web/geek/job?encryptId=boss-product-intern-002",
        description="负责产品需求调研、竞品分析、原型文档整理，并跟进研发和测试环节的问题闭环。",
        requirements="本科及以上在读，熟悉产品文档和数据分析，沟通主动，能够每周到岗四天以上。",
        sync_metadata={
            "detail_complete": True,
            "observed_detail_url": "https://www.zhipin.com/web/geek/job?encryptId=boss-product-intern-002",
            "blockers": [],
            "missing_fields": [],
        },
        _runtime_constraints={"plan_kind": "jd_sync"},
    )

    assert stored["action"] == "created"
    assert stored["job_description"]["source"] == "jd_sync"


class _FakeUrlResponse:
    def __init__(self, body: str) -> None:
        self._body = body

    def __enter__(self) -> "_FakeUrlResponse":
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return self._body.encode("utf-8")
