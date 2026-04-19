# 发现候选人

- key: candidate_discovery
- display_order: 30
- goal_kind: candidate_discovery
- requires_jd: true
- supports_candidate_count_target: true
- default_candidate_count_target: 3
- direct_runnable: false

## Summary

围绕指定 JD，在 human 当前使用的普通浏览器（非 AI 模式浏览器）里的 zhipin.com 上筛选候选人，并把有效候选人写入工作区。

## Goal Text

围绕指定 JD，在 human 当前使用的普通浏览器（非 AI 模式浏览器）里的 zhipin.com 上筛选候选人，将有效候选人写入工作区，并补齐基础联系信息；若该普通浏览器里尚未打开 zhipin.com，则引导 human 打开相关候选人页面后继续。

## Constraints

- scope_kind: job
- memory_scope_kind: job
- target_entity: candidate

## Success Criteria

- entity: candidate
- outcome: candidate_discovery

## Context Hints

- trigger: scene_template_panel
