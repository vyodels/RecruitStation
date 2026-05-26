# 同步 JD（初始）

- key: sync_jd_initial
- display_order: 10
- action_kind: sync_jd_initial
- requires_jd: false
- supports_candidate_count_target: false
- direct_runnable: true

## Summary

优先复用 human 当前使用的普通浏览器（非 AI 模式浏览器）中已打开且可继续任务的招聘平台 JD 页面；优先使用 `browser_list_tabs` 检查普通浏览器里是否已有可复用目标页。只有在当前可达范围内确实没有可复用目标页时，才由 Agent 自行打开并进入可执行招聘页面。只把当前仍处于活跃招聘中的 JD 及其可确认详情首次同步到共享工作区 JD 库。雇主端可编辑岗位表单或岗位管理详情在展示真实岗位字段时可作为 JD 详情来源；候选人列表、沟通/消息页或投递推进页不能作为同步进度。

## Instruction

在 human 当前使用的普通浏览器（非 AI 模式浏览器）中完成 JD 初始同步：先复用已打开且可继续任务的招聘平台 JD 页面；优先使用 `browser_list_tabs` 检查普通浏览器里是否已有可复用目标页。只有在当前工具可达范围内确实没有可复用目标页时，才由 Agent 自行打开并进入可执行招聘页面。读取可确认的岗位列表与详情，只把当前仍处于活跃招聘中的 JD 及其可确认详情首次写入共享工作区，跳过已关闭、已下线、已归档、已过期、已停止招聘或状态不明确的岗位。雇主端可编辑岗位表单、岗位管理详情或等价详情区域在展示真实岗位标题、地点、薪酬、经验、学历、描述、职责、要求等字段时可作为 JD 详情来源；写入本地 `description` 时保留页面可见原文，可以把页面拆开的职位描述/职责/任职要求合并成一个“职位描述”正文，不要写成“已可见/包含/聚焦/等内容”这类观察摘要。读取后可用页面可见关闭、返回或岗位管理导航回到列表；候选人列表、沟通/消息页或投递推进页不能作为 JD 详情读取进度或完成证据。只有在登录、验证码、权限、设备绑定或其它明确的 human-only blocker 下，才请求 human 协助，并在结束时汇总 `created`、`updated`、`skipped`、`blocked`。

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
- write_policy: upsert_all_confirmed_active_roles

## Context Hints

- trigger: scene_template_panel
