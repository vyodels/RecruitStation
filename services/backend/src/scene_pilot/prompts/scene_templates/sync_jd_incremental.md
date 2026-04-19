# 同步 JD（增量）

- key: sync_jd_incremental
- display_order: 20
- goal_kind: sync_jd_incremental
- requires_jd: false
- supports_candidate_count_target: false
- direct_runnable: true

## Summary

从 human 当前使用的普通浏览器（非 AI 模式浏览器）中已打开且可访问的 zhipin.com 招聘页面读取岗位，与共享工作区 JD 库做差异对比后增量同步。

## Goal Text

从 human 当前使用的普通浏览器（非 AI 模式浏览器）中已打开且可访问的 zhipin.com 招聘页面读取 JD，与共享工作区现有 JD 做差异对比后执行增量同步；只新建缺失岗位、更新已变化岗位、跳过未变化岗位，不重复创建。若该普通浏览器里尚未打开 zhipin.com，则引导 human 打开正确页面后继续，并在结束时汇总 created、updated、skipped、blocked。

## Constraints

- sync_mode: incremental
- scope_kind: global
- memory_scope_kind: global
- target_entity: job_description
- source_surface: browser_accessible_recruiting_pages
- target_store: shared_workspace_job_descriptions
- sync_strategy: compare_remote_roles_with_workspace_then_upsert_deltas
- missing_remote_role_policy: no_delete_without_explicit_instruction

## Success Criteria

- mode: incremental
- entity: job_description
- source: browser_accessible_recruiting_pages
- target: shared_workspace_job_descriptions
- write_policy: upsert_changed_roles_skip_unchanged

## Context Hints

- trigger: scene_template_panel
