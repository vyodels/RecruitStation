# Recruit Agent Handoff

## 当前结论

`2026-04-15` 之后，这个仓库的有效产品方向已经收束为 `Recruit Agent`，不再把自己定义成早期执行控制台。

当前主语是：

- 招聘 Agent 配置
- 候选人进度与沟通确认
- Candidate / JD / Global memory
- skill 管理与自学习演进治理

底层仍保留 runtime、plan、episode 等执行内核，但它们已经下沉为实现层，不再作为顶层产品对象。

## 当前已完成

- 桌面导航已改为 `概览 / 招聘 Agent / 工作台 / 沟通中心 / 自学习/演进 / 设置`
- `RecruitAgentProfile`、隔离 memory、skill 管理、候选人线程与演进审批已经落地
- 工作台已围绕候选人进度和 agent 运行结果重构
- 旧的编排中心化桌面页面已从前端主产品面中清理
- 后端仍保留兼容执行内核，但显示名称和文档已经转到 `Recruit Agent`

## 继续接手时先看

- [README.md](../README.md)
- [Plan.md](../Plan.md)
- [apps/desktop/src/features/workspace/DesktopWorkspace.tsx](../apps/desktop/src/features/workspace/DesktopWorkspace.tsx)
- [apps/desktop/src/features/recruit-agent/RecruitAgentView.tsx](../apps/desktop/src/features/recruit-agent/RecruitAgentView.tsx)
- [apps/desktop/src/features/communications/CommunicationsView.tsx](../apps/desktop/src/features/communications/CommunicationsView.tsx)
- [services/backend/src/scene_pilot/services/recruit_agent.py](../services/backend/src/scene_pilot/services/recruit_agent.py)
- [services/backend/src/scene_pilot/api/routers/recruit_agent.py](../services/backend/src/scene_pilot/api/routers/recruit_agent.py)

## 验证命令

```bash
python3 -m pytest services/backend/tests -q
npm run desktop:typecheck
```

## 历史说明

仓库的实现目录结构沿用当前工程布局，但对外 CLI、桌面启动入口和环境变量前缀已经统一切到 `recruit-agent` / `RECRUIT_AGENT_`。
