# 旧运行时架构历史归档

这份文档描述的是仓库早期的通用 runtime 方向，已经不再代表当前产品路线。

## 当前状态

当前产品方向已经切到 `Recruit Agent`：

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
