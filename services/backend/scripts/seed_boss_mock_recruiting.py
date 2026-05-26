from __future__ import annotations

from pathlib import Path
from typing import Any

from recruit_station.core.settings import load_settings
from recruit_station.db.session import create_engine_from_settings, create_session_factory, initialize_database
from recruit_station.plugins.recruit.toolkit import attach_resume_artifact, upsert_candidate, upsert_job_description
from recruit_station.repositories import CandidateApplicationRepository, ResumeArtifactRepository


RESUME_ROOT = Path("/Users/vyodels/AgentProjects/mcp-browser-chrome/scripts/fixtures/boss-like")
PLATFORM = "boss_like_mock_live"


JOBS: list[dict[str, Any]] = [
    {
        "external_id": "jd-sales-001",
        "title": "国际销售工程师",
        "company_name": "星瀚智能制造",
        "department": "海外销售部",
        "location": "上海",
        "owner": "周岚",
        "headcount": 2,
        "salary_min": 25000,
        "salary_max": 42000,
        "compensation_text": "25k-42k · 14薪",
        "experience_requirement": "3-5 年 B2B 海外销售经验",
        "education_requirement": "本科及以上",
        "summary": "负责海外大客户开拓、线索跟进、方案沟通和销售闭环。",
        "requirements": "英语可作为工作语言；熟悉 CRM；具备制造业或 SaaS 出海销售经验优先。",
        "tags": ["海外业务", "B2B 销售", "英文演示"],
    },
    {
        "external_id": "jd-solution-002",
        "title": "解决方案顾问",
        "company_name": "星瀚智能制造",
        "department": "售前咨询部",
        "location": "北京",
        "owner": "林知夏",
        "headcount": 2,
        "salary_min": 30000,
        "salary_max": 48000,
        "compensation_text": "30k-48k · 13薪",
        "experience_requirement": "4-8 年售前咨询或解决方案经验",
        "education_requirement": "本科及以上",
        "summary": "支持售前演示、需求澄清、方案架构和跨团队交付协同。",
        "requirements": "需要复杂项目沟通经验，能把客户场景转化为方案和交付边界。",
        "tags": ["售前咨询", "方案架构", "企业客户"],
    },
    {
        "external_id": "jd-csm-003",
        "title": "客户成功经理",
        "company_name": "星瀚智能制造",
        "department": "客户成功部",
        "location": "深圳",
        "owner": "何安",
        "headcount": 3,
        "salary_min": 22000,
        "salary_max": 36000,
        "compensation_text": "22k-36k · 14薪",
        "experience_requirement": "4 年以上 B2B 客户成功或实施交付经验",
        "education_requirement": "本科及以上",
        "summary": "负责重点客户上线、续约增长、风险预警和跨部门问题闭环。",
        "requirements": "熟悉 B2B 客户经营，能处理复杂干系人和续约增长目标。",
        "tags": ["客户经营", "续约增长", "项目推进"],
    },
    {
        "external_id": "jd-pm-004",
        "title": "数据产品经理",
        "company_name": "星瀚智能制造",
        "department": "数据产品部",
        "location": "杭州",
        "owner": "顾南",
        "headcount": 1,
        "salary_min": 28000,
        "salary_max": 45000,
        "compensation_text": "28k-45k · 14薪",
        "experience_requirement": "5 年以上数据产品或经营分析产品经验",
        "education_requirement": "本科及以上",
        "summary": "负责经营分析、指标体系、数据产品规划和需求优先级管理。",
        "requirements": "要求指标体系、SQL、数据治理和跨团队产品推进经验。",
        "tags": ["数据产品", "指标体系", "SQL"],
    },
    {
        "external_id": "jd-backend-005",
        "title": "后端平台工程师",
        "company_name": "星瀚智能制造",
        "department": "技术平台部",
        "location": "广州",
        "owner": "沈砚",
        "headcount": 2,
        "salary_min": 32000,
        "salary_max": 52000,
        "compensation_text": "32k-52k · 15薪",
        "experience_requirement": "5 年以上服务端平台或业务系统经验",
        "education_requirement": "本科及以上",
        "summary": "建设招聘与销售业务平台的服务端能力，保障接口稳定性和数据一致性。",
        "requirements": "需要 Python/Go/Java 任一主语言经验，熟悉队列、事务、观测和服务治理。",
        "tags": ["平台工程", "高并发", "服务治理"],
    },
]

NAMES_BY_JOB = {
    "jd-sales-001": ["李青", "陈舟", "王梓涵", "赵明远", "刘思雨", "孙嘉诚", "周若琪", "吴昊然", "郑一鸣", "黄嘉宁"],
    "jd-solution-002": ["许景行", "马亦辰", "罗舒雅", "宋承泽", "梁语桐", "韩墨", "唐钰", "董思远", "贺清越", "钱若琳"],
    "jd-csm-003": ["冯嘉木", "蒋安琪", "余文博", "邹雨辰", "叶知秋", "程浩宇", "曹昕", "薛嘉言", "袁芷晴", "潘明哲"],
    "jd-pm-004": ["顾以宁", "陆星河", "范知微", "白子昂", "任可欣", "孟书言", "石沐阳", "方诗涵", "秦朗", "戴雨桐"],
    "jd-backend-005": ["沈亦舟", "姜云深", "邵子墨", "夏清和", "钟辰", "叶怀瑾", "林远航", "施雨乔", "龙皓", "苏明熙"],
}

ROLE_FACTS = {
    "jd-sales-001": (["海外销售经理", "大客户销售", "国际业务拓展", "渠道销售负责人"], ["英文演示", "东南亚市场", "CRM", "重点客户推进"]),
    "jd-solution-002": (["售前顾问", "解决方案架构师", "行业顾问", "交付型售前"], ["方案澄清", "POC 管理", "企业客户", "跨团队协作"]),
    "jd-csm-003": (["客户成功经理", "续约经理", "实施顾问", "客户运营负责人"], ["续约增长", "客户健康度", "上线推进", "风险预警"]),
    "jd-pm-004": (["数据产品经理", "BI 产品经理", "策略产品经理", "经营分析产品"], ["指标体系", "SQL", "数据治理", "需求优先级"]),
    "jd-backend-005": (["后端工程师", "平台工程师", "服务端负责人", "架构工程师"], ["Python", "消息队列", "服务治理", "可观测性"]),
}

STATUS_PLAN = [
    ("online_resume_acquired", "resume_acquired", "M05", 86, "recommended", True, True),
    ("profile_ready", "profile_ready", "M09", 82, "recommended", True, True),
    ("interview_pending", "interview_pending", "M13", 88, "strong_recommend", True, True),
    ("interview_scheduled", "interview_scheduled", "M14", 91, "strong_recommend", True, True),
    ("interview_passed", "interview_passed", "M16", 93, "offer_recommend", True, True),
    ("offer_sent", "offer_sent", "M18", 89, "offer_sent", True, True),
    ("offer_accepted", "offer_accepted", "M19", 95, "hired", True, True),
    ("online_resume_rejected", "online_resume_rejected", "M06", 62, "not_now", True, True),
    ("online_resume_fetching", "online_resume_fetching", "M04", 74, "pending_resume", False, False),
    ("profile_ready", "profile_ready", "M09", 80, "recommended", True, True),
]


def candidate_external_id(job_external_id: str, index: int) -> str:
    if job_external_id == "jd-sales-001" and index == 0:
        return "mock-live-candidate-li-qing-613"
    return f"mock-live-{job_external_id}-candidate-{index + 1:02d}"


def resume_file_name(candidate_id: str) -> str:
    if candidate_id == "mock-live-candidate-li-qing-613":
        return "li-qing-resume.pdf"
    return f"{candidate_id}.pdf"


def has_artifact(session_factory, application_id: str, file_name: str) -> bool:
    with session_factory() as session:
        return any(item.file_name == file_name for item in ResumeArtifactRepository(session).by_application(application_id, limit=200))


def update_application_score(session_factory, application_id: str, *, score: int, decision: str, skills: list[str]) -> None:
    with session_factory() as session:
        repo = CandidateApplicationRepository(session)
        application = repo.get(application_id)
        if application is None:
            raise KeyError(f"candidate application {application_id} not found")
        repo.update(
            application,
            {
                "ai_scores": {
                    "overall": score,
                    "decision": decision,
                    "dimension_scores": {
                        "role_match": min(score + 2, 100),
                        "experience": max(score - 3, 0),
                        "communication": max(score - 6, 0),
                    },
                    "evidence_refs": skills,
                    "rubric_version": "boss-mock-recruit-scorecard-v1",
                },
                "ai_reasoning": f"Mock 评分：候选人在 {', '.join(skills)} 方面与目标岗位匹配，结论 {decision}。",
            },
        )


def seed() -> dict[str, Any]:
    settings = load_settings()
    engine = create_engine_from_settings(settings)
    initialize_database(engine)
    session_factory = create_session_factory(engine)

    job_ids: list[str] = []
    application_ids: list[str] = []
    artifacts_created = 0

    for job_index, job in enumerate(JOBS):
        stored_job = upsert_job_description(
            session_factory,
            title=job["title"],
            company_name=job["company_name"],
            department=job["department"],
            location=job["location"],
            employment_type="全职",
            headcount=job["headcount"],
            salary_min=job["salary_min"],
            salary_max=job["salary_max"],
            compensation_text=job["compensation_text"],
            experience_requirement=job["experience_requirement"],
            education_requirement=job["education_requirement"],
            summary=job["summary"],
            description=f"{job['summary']} {job['requirements']}",
            requirements=job["requirements"],
            benefit_tags=["五险一金", "绩效奖金", "补充医疗"],
            detail_metadata={"owner": job["owner"], "mockSource": "boss-like-live-validation", "externalId": job["external_id"]},
            status="active",
            source="mock_live_validation",
            platform=PLATFORM,
            external_id=job["external_id"],
            external_url=f"http://127.0.0.1/mock/jobs/{job['external_id']}",
            sync_metadata={"source": "boss_like_mock_live", "candidateTarget": 10},
        )
        job_id = stored_job["job_description"]["job_description_id"]
        job_ids.append(job_id)
        titles, skills = ROLE_FACTS[job["external_id"]]

        for candidate_index, name in enumerate(NAMES_BY_JOB[job["external_id"]]):
            status, stage, milestone, score, decision, has_resume, has_contact = STATUS_PLAN[candidate_index]
            candidate_id = candidate_external_id(job["external_id"], candidate_index)
            years = 3 + ((candidate_index + len(job["external_id"])) % 7)
            title = titles[candidate_index % len(titles)]
            skill_a = skills[candidate_index % len(skills)]
            skill_b = skills[(candidate_index + 1) % len(skills)]
            phone = f"138{61000000 + job_index * 1000 + candidate_index:08d}" if has_contact else None
            email = f"{candidate_id.replace('mock-live-', '').replace('-', '.')}@example.test" if has_contact else None
            contact_info = (
                {"channels": [{"type": "phone", "value": phone}, {"type": "email", "value": email}], "phone": phone, "email": email}
                if has_contact
                else {"channels": []}
            )
            resume_text = f"{name}，{years} 年{title}经验，最近负责{job['location']}及跨区域客户场景，核心能力包括{skill_a}、{skill_b}和复杂项目推进。"
            file_name = resume_file_name(candidate_id)
            file_path = str(RESUME_ROOT / file_name)
            if not (RESUME_ROOT / file_name).exists():
                file_path = str(RESUME_ROOT / "li-qing-resume.pdf")

            stored_candidate = upsert_candidate(
                session_factory,
                name=name,
                platform=PLATFORM,
                platform_candidate_id=candidate_id,
                contact_info=contact_info,
                resume_path=file_path if has_resume else None,
                online_resume_text=resume_text,
                profile_url=f"http://127.0.0.1/mock/candidate/{candidate_id}",
                raw_profile={
                    "current_title": title,
                    "city": job["location"],
                    "years": years,
                    "skills": [skill_a, skill_b],
                    "source": "boss-like mock",
                },
                job_description_id=job_id,
                platform_application_id=f"{job['external_id']}-{candidate_id}",
                current_status=status,
                current_stage_key=stage,
                deepest_milestone=milestone,
                state_snapshot={
                    "current_stage_key": stage,
                    "contact_acquired": has_contact,
                    "contact_channels": ["phone", "email"] if has_contact else [],
                    "resume_status": "received" if has_resume else "fetching",
                    "ai_assessment_status": "completed",
                },
                application_metadata={
                    "mock_source": "boss_like_live_validation",
                    "candidate_rank": candidate_index + 1,
                    "source_observation": {"mockSite": "boss-like", "candidateUrl": f"/candidate/{candidate_id}"},
                },
                source_platform=PLATFORM,
            )
            application_id = stored_candidate["application"]["application_id"]
            application_ids.append(application_id)
            update_application_score(
                session_factory,
                application_id,
                score=score,
                decision=decision,
                skills=[skill_a, skill_b],
            )

            if has_resume and not has_artifact(session_factory, application_id, file_name):
                attach_resume_artifact(
                    session_factory,
                    application_id=application_id,
                    source=PLATFORM,
                    artifact_type="resume",
                    file_name=file_name,
                    file_path=file_path,
                    extracted_text=resume_text,
                    contact_snapshot=contact_info,
                    metadata={"mockSource": "boss-like-live-validation", "score": score, "decision": decision},
                )
                artifacts_created += 1

    return {
        "jobs": len(job_ids),
        "applications": len(application_ids),
        "artifacts_created": artifacts_created,
        "job_ids": job_ids,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(seed(), ensure_ascii=False, indent=2))
