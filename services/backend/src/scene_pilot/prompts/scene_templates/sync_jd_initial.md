# 同步 JD（初始）

- key: sync_jd_initial
- display_order: 10
- goal_kind: sync_jd_initial
- requires_jd: false
- supports_candidate_count_target: false
- direct_runnable: true

## Summary

从 human 当前使用的普通浏览器（非 AI 模式浏览器）中已打开且可访问的 zhipin.com 招聘页面读取岗位，首次全量写入共享工作区的 JD 库。

## Goal Text

从 human 当前使用的普通浏览器（非 AI 模式浏览器）中已打开且可访问的 zhipin.com 招聘页面读取 JD，首次全量同步到共享工作区的 JD 库；逐条检查可见岗位列表与详情，把每个确认岗位写入工作区。若该普通浏览器里尚未打开 zhipin.com，则引导 human 打开正确页面后继续，并在结束时汇总 created、updated、skipped、blocked。

## Constraints

- sync_mode: initial
- scope_kind: global
- memory_scope_kind: global
- target_entity: job_description
- source_surface: browser_accessible_recruiting_pages
- target_store: shared_workspace_job_descriptions
- sync_strategy: scan_remote_roles_and_upsert_all_confirmed_roles

## Success Criteria

- mode: initial
- entity: job_description
- source: browser_accessible_recruiting_pages
- target: shared_workspace_job_descriptions
- write_policy: upsert_all_confirmed_roles

## Context Hints

- trigger: scene_template_panel
