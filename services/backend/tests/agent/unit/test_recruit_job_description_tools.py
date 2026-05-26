from __future__ import annotations

import pytest

from recruit_station.core.settings import AppSettings
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


def test_upsert_job_description_uses_detail_metadata_external_identity(tmp_path) -> None:
    container = _build_container(tmp_path)

    created = upsert_job_description(
        container.session_factory,
        title="产品实习生",
        location="北京",
        source="jd_sync",
        detail_metadata={
            "source": "zhipin employer job edit page",
            "external_id": "boss-job-001",
            "external_url": "https://www.zhipin.com/web/chat/job/edit?encryptId=boss-job-001",
        },
    )
    updated = upsert_job_description(
        container.session_factory,
        title="产品实习生",
        location="北京朝阳区",
        source="jd_sync",
        detail_metadata={
            "source": "zhipin employer job edit page",
            "external_id": "boss-job-001",
            "external_url": "https://www.zhipin.com/web/chat/job/edit?encryptId=boss-job-001",
        },
    )

    assert updated["action"] == "updated"
    assert created["job_description"]["job_description_id"] == updated["job_description"]["job_description_id"]
    assert updated["platform_identity"]["platform"] == "zhipin"
    assert updated["platform_identity"]["external_id"] == "boss-job-001"
    assert len(list_job_descriptions(container.session_factory)) == 1


def test_upsert_job_description_reuses_matching_detail_fingerprint_when_title_is_category(tmp_path) -> None:
    container = _build_container(tmp_path)
    description = "负责 B 端、数据产品、中后台产品以及 AI 产品的需求分析、产品设计和迭代。"
    requirements = "本科及以上学历，计算机科学、人工智能或相关专业优先。"

    created = upsert_job_description(
        container.session_factory,
        title="产品实习生",
        location="北京朝阳区建外SOHO东区B座20层2003室",
        compensation_text="2k-4k",
        description=description,
        requirements=requirements,
        source="jd_sync",
        detail_metadata={
            "source": "zhipin employer job edit page",
            "external_id": "boss-job-002",
        },
    )
    updated = upsert_job_description(
        container.session_factory,
        title="AI产品经理",
        location="北京朝阳区建外SOHO东区B座20层2003室",
        compensation_text="2k-4k",
        description=description,
        requirements=requirements,
        source="jd_sync",
        detail_metadata={"source": "zhipin employer job edit page"},
    )

    assert updated["action"] == "updated"
    assert created["job_description"]["job_description_id"] == updated["job_description"]["job_description_id"]
    assert len(list_job_descriptions(container.session_factory)) == 1


def test_jd_sync_combines_original_requirements_into_description(tmp_path) -> None:
    container = _build_container(tmp_path)

    stored = upsert_job_description(
        container.session_factory,
        title="产品实习生",
        description="负责 B 端、数据产品、中后台产品以及 AI 产品的需求分析、产品设计和迭代。",
        requirements="本科及以上学历，计算机科学、人工智能或相关专业优先。",
        source="jd_sync",
        detail_metadata={
            "source": "zhipin employer job edit page",
            "external_id": "boss-job-003",
        },
        sync_metadata={
            "detail_complete": True,
            "observed_detail_url": "https://www.zhipin.com/web/chat/job/edit?encryptId=boss-job-003",
            "blockers": [],
            "missing_fields": [],
        },
    )

    assert stored["job_description"]["description"] == (
        "负责 B 端、数据产品、中后台产品以及 AI 产品的需求分析、产品设计和迭代。\n\n"
        "任职要求：\n"
        "本科及以上学历，计算机科学、人工智能或相关专业优先。"
    )
    assert stored["job_description"]["requirements"] is None


def test_jd_sync_prefers_original_metadata_over_observation_summary(tmp_path) -> None:
    container = _build_container(tmp_path)

    stored = upsert_job_description(
        container.session_factory,
        title="产品实习生",
        description="岗位描述已可见，包含需求分析、产品设计等内容。",
        requirements="任职要求已可见，包含本科及以上、AI 热情等内容。",
        source="jd_sync",
        detail_metadata={
            "source": "zhipin employer job edit page",
            "external_id": "boss-job-004",
            "responsibilities": [
                "负责B端、数据产品、中后台产品以及AI产品的需求分析、产品设计和迭代，确保产品满足市场和客户需求",
                "制定产品策略和规划，协调跨部门资源，确保产品按时发布和更新",
            ],
            "requirements": [
                "本科及以上学历，计算机科学、人工智能或相关专业优先",
                "对AI领域有热情，乐于应对挑战，具备团队合作精神和解决问题的能力",
            ],
        },
        sync_metadata={
            "detail_complete": True,
            "observed_detail_url": "https://www.zhipin.com/web/chat/job/edit?encryptId=boss-job-004",
            "blockers": [],
            "missing_fields": [],
        },
    )

    assert "岗位描述已可见" not in stored["job_description"]["description"]
    assert "任职要求已可见" not in stored["job_description"]["description"]
    assert "负责B端、数据产品" in stored["job_description"]["description"]
    assert "任职要求：\n本科及以上学历" in stored["job_description"]["description"]
    assert stored["job_description"]["requirements"] is None


def test_jd_sync_does_not_overwrite_original_description_with_summary(tmp_path) -> None:
    container = _build_container(tmp_path)
    original_description = "负责 B 端产品需求分析和产品设计。"

    created = upsert_job_description(
        container.session_factory,
        title="产品实习生",
        description=original_description,
        requirements="本科及以上学历。",
        source="jd_sync",
        detail_metadata={
            "source": "zhipin employer job edit page",
            "external_id": "boss-job-005",
        },
    )
    updated = upsert_job_description(
        container.session_factory,
        title="产品实习生",
        description="岗位描述已可见，包含 B 端产品需求分析等内容。",
        requirements="任职要求已可见，包含本科及以上等内容。",
        source="jd_sync",
        detail_metadata={
            "source": "zhipin employer job edit page",
            "external_id": "boss-job-005",
        },
    )

    assert updated["action"] == "updated"
    assert updated["job_description"]["job_description_id"] == created["job_description"]["job_description_id"]
    assert updated["job_description"]["description"].startswith(original_description)
    assert "已可见" not in updated["job_description"]["description"]


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


class _FakeUrlResponse:
    def __init__(self, body: str) -> None:
        self._body = body

    def __enter__(self) -> "_FakeUrlResponse":
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return self._body.encode("utf-8")
