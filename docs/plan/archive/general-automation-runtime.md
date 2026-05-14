# 旧运行时架构历史归档

> Status: archived
> Supersedes: -
> Superseded by: docs/specs/2026-04-20-agent-product-design-principles.md; docs/specs/2026-04-20-dual-agent-product-architecture.md
> Distilled into: -
> Last reviewed against code: 2026-04-20
> Legacy path retained: docs/general-automation-runtime.md

这份文档描述的是仓库早期的通用 runtime 方向，已经不再代表当前产品路线。

## 当前状态

当前产品方向已经切到 `RecruitStation`：

- 招聘 Agent 配置与外露治理
- 候选人进度管理
- 候选人沟通确认
- Candidate / JD / Global memory
- skill 与演进审批

## 这份文档为什么还保留

因为仓库底层仍然存在一部分 runtime 内核实现，例如：

- `TaskSpec`
- `ExecutionPlan`
- `ExecutionEpisode`
- runtime replay / patch / scene assessment

这些对象现在属于实现层，而不是顶层产品模型。

## 现在应该读什么

如果你要理解当前仓库，请优先阅读：

- [Plan.md](../Plan.md)
- [README.md](../README.md)
- [docs/project-handoff.md](./project-handoff.md)

如果你只是在追溯底层执行内核的来源，再回来看这份历史文档。
