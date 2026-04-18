# Agent v2 直接切换实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不保留兼容路径、不做迁移过渡、不保留旧 runtime/orchestration 代码的前提下，把当前 Recruit Agent 后端直接切换到新的 Agent v2 架构：共享的纯粹 Kernel、`AutonomousAgent`、`AssistantAgent`、Scenario Capability Pack（招聘场景包）、Memory / Compact / Evolution / Plugin / MCP / Execution Unit 全套落地，并完成自动化测试闭环。

**Architecture:** 这是一次**直接切换（direct cutover）**，不是兼容升级。新的后端唯一运行路径是 `agents/ + kernel/ + runtime_v2/ + memory/ + assistant/ + execution_units/ + plugins/ + mcp_v2/ + evolution/ + skills/`。Kernel 只保留通用原语与扩展插槽，不允许知道“招聘”是什么；招聘的候选人接管、handover、外部触达限制、招聘 prompt 片段、招聘 API 都必须下沉为 `plugins/recruit/` 能力包，通过 `PluginHost` 挂载。所有与旧执行合同、旧队列控制、旧 context assembler、旧 autonomy service 相关的代码，在新路径打通后必须删除，绝不保留以免混淆。

**Tech Stack:** FastAPI、SQLAlchemy ORM、SQLite、Alembic、Pydantic、Anthropic/OpenAI-compatible provider、SSE/WebSocket、Python >= 3.14、TypeScript desktop client（仅做接口/类型同步，不做自动 UI 验证）。

---

## 0. 本计划的地位与执行约束

### 0.1 本计划是唯一实施依据

从现在开始，**本计划要完全替代**：
- `docs/agent-v2-implementation-spec.md`
- `docs/agent-v2-design-summary.md`

Codex 在实施时**不需要再额外阅读上述两个文档**。如果两者与本计划有冲突，**以本计划为准**。

### 0.2 强约束（Codex 不得自行发挥）

- 不做兼容层。
- 不做双路径。
- 不做 feature flag 灰度。
- 不做 backfill / 数据迁移说明。
- 不保留旧 dead branch。
- 不保留旧 `services/agent.py` / `services/context_assembler.py` / `runtime/agent_loop.py` / `services/autonomy.py` / `services/runtime_control.py` / `services/runtime.py` / `api/routers/runtime.py`。
- 不把招聘语义写进 Kernel-facing 契约。
- 不新建平行 `v2_*` 表。
- 不新建统一 `memory_items` 表。
- 不把 candidate lock / handover / recruit prompt 规则放回 Kernel。
- 若旧代码在某个任务结束后已无必要，必须在该任务中直接删除。

### 0.3 UI 测试策略

- **自动化范围**：后端单测、集成测试、端到端 backend flow、必要的 desktop typecheck。
- **暂缓范围**：真实 UI 行为验证、桌面端交互 smoke、SSE 前端表现、视觉检查。
- **执行方式**：UI 测试在实现完成后，由 human 监督下进行手动验收。
- Codex 不需要自动做 UI 交互测试，但如果 API/类型改动导致前端编译失败，必须同步修到 `npm run desktop:typecheck` 通过。

### 0.4 测试策略（Codex 必须自主补测试）

Codex 不得只写实现不写测试。每个任务必须：
1. 先补最小失败测试；
2. 再补实现；
3. 运行对应最小测试；
4. 每个大阶段补集成测试；
5. 最后运行全量 backend 测试；
6. 如触及 desktop API/types，再跑 `npm run desktop:typecheck`。

### 0.5 唯一允许中途停止的情况

只有以下情况允许 Codex 中途停下来：
1. 仓库现状与本计划存在真正不可自解的矛盾；
2. 需要外部密钥/账户/服务授权才能继续验证；
3. 测试失败暴露的是本计划内部矛盾，而不是代码 bug。

除此之外，必须一口气执行到底。

---

## 1. 最终系统目标（Codex 必须先建立正确心智模型）

### 1.1 系统最终结构

最终系统由两类 agent 共享一套底层 Kernel：

- `AutonomousAgent`
  - 由 `Heartbeat` 驱动 tick
  - 面向长期 run
  - 负责自主推进、观察、记忆、调度、自唤醒
- `AssistantAgent`
  - 由用户消息驱动 turn
  - 面向 conversation
  - 负责流式对话、工具调用、人工确认、取消 turn

它们共享：
- `AgentKernel`
- `ToolBus`
- `MemoryService`
- `PluginHost`
- `LearningWriter`
- `GuardPolicy`
- provider / MCP / Skill / Evolution 设施

### 1.2 Kernel 的边界

Kernel 永远不知道“招聘”是什么。Kernel 只知道：
- Goal
- State
- Checkpoint
- Log
- Memory
- Tick / Turn
- ToolCall
- Guard
- PluginHost 扩展位
- scope / scope_ref / scope_kind

Kernel 不能知道：
- JD
- candidate
- JobAssembly
- RecruitAgentProfile
- 候选人接管锁
- handover
- 招聘特有的外部触达限制
- 招聘 prompt 文案

### 1.3 招聘能力必须在哪里实现

招聘能力必须作为 `Scenario Capability Pack` 提供，挂载在 `PluginHost` 上。

当前唯一场景包：`plugins/recruit/`

它承载：
- 候选人接管锁
- handover / release note / next hint
- `take_over_candidate` / `release_candidate` / `list_locked_candidates`
- Observation enrichers（`human_locked` / `recent_handover`）
- Guard checks（被接管候选人禁止动作；Assistant 外部动作前必须满足全局 pause 条件）
- recruit persona fragment
- recruit 专属 API router

### 1.4 两层分工

| 层 | 负责什么 | 不能负责什么 |
|---|---|---|
| Kernel / core | 通用 runtime 原语、状态流、hook surface、Tool/MCP/Skill/Memory/Guard 机制 | 招聘语义、候选人锁、JD 规则、hand over 文案 |
| Scenario Capability Pack | 某个业务场景的特定语义、特定工具、特定 Observation 字段、特定 Guard 规则、特定 API | 改写 Kernel 核心节点职责 |

### 1.5 五原语必须保留

Autonomous 主线连续性依赖：
- `Goal`
- `State`
- `Checkpoint`
- `Log`
- `Memory`

不能退回到：
- 大量 agenda/work item 驱动主线
- 靠超长 messages 记住执行历史
- 把页面噪音直接背进主线

### 1.6 Assistant 取消语义必须保留

Assistant 必须支持像 Claude Code 一样的 turn cancel：
- 每个 turn 持有 `CancellationToken`
- 支持 `/api/assistant/conversations/{id}/cancel`
- 支持 SSE 断开自动 cancel
- 不回滚已写副作用
- partial outputs 进入 jsonl 与 conversation history

Autonomous tick 不允许中途 kill。

---

## 2. 当前代码现状（基于仓库实际代码，不是理想结构）

### 2.1 当前主要 runtime/orchestration 路径

当前后端主路径大致是：

- `services/backend/src/scene_pilot/server.py`
  - 创建 FastAPI app
  - 启动 `AutonomyLoopService`
- `services/backend/src/scene_pilot/services/container.py`
  - 构建 provider、tool registry、scheduler、`AgentLoop`、`AgentControlService`
- `services/backend/src/scene_pilot/services/agent.py`
  - 当前 orchestration 核心
  - enqueue / run / sourcing / retry / progression / follow-up 工厂
- `services/backend/src/scene_pilot/services/autonomy.py`
  - 当前 autonomy poll loop
- `services/backend/src/scene_pilot/services/runtime_control.py`
  - 当前 run/session/work_item 生命周期编排
- `services/backend/src/scene_pilot/services/runtime.py`
  - 当前 execution plan / episode / trace 等 runtime 持久化
- `services/backend/src/scene_pilot/services/context_assembler.py`
  - 当前 context fragment 组装
- `services/backend/src/scene_pilot/runtime/agent_loop.py`
  - 当前 LLM 循环、tool 执行、execution_contract 逻辑
- `services/backend/src/scene_pilot/runtime/prompts.py`
  - 当前 prompt 拼装
- `services/backend/src/scene_pilot/api/routers/runtime.py`
  - 当前 execution/runtime API
- `services/backend/src/scene_pilot/api/routers/recruit_agent.py`
  - 当前 recruit-agent profile/memory/runtime surfaces

### 2.2 当前可复用的持久化基础

可以直接扩，不要平行重建：
- `models/domain.py`
- `repositories/domain.py`
- 已有的：
  - `AgentRun`
  - `AgentRunCheckpoint`
  - `AgentRuntimeEvent`
  - `GoalSpec`
  - `ApprovalItem`
  - `OperatorInteraction`
  - `RecruitAgentProfile`
  - memory 表
  - `Skill`
  - `McpServer`

### 2.3 当前明显应该被清掉的旧路径

最终切换后，不允许继续存在为运行真相源：
- `services/backend/src/scene_pilot/services/agent.py`
- `services/backend/src/scene_pilot/services/context_assembler.py`
- `services/backend/src/scene_pilot/services/autonomy.py`
- `services/backend/src/scene_pilot/services/runtime_control.py`
- `services/backend/src/scene_pilot/services/runtime.py`
- `services/backend/src/scene_pilot/runtime/agent_loop.py`
- `services/backend/src/scene_pilot/runtime/prompts.py`
- `services/backend/src/scene_pilot/api/routers/runtime.py`
- `services/backend/src/recruit_agent/server.py`
- `services/backend/src/recruit_agent/core/app.py`

---

## 3. 最终目录结构（实现完成后应接近此形态）

```text
services/backend/src/scene_pilot/
├── agents/
│   ├── autonomous.py
│   ├── assistant.py
│   ├── assembly.py
│   └── heartbeat.py
├── kernel/
│   ├── kernel.py
│   ├── sense.py
│   ├── assemble.py
│   ├── deliberate.py
│   ├── guard.py
│   ├── act.py
│   ├── update_memory.py
│   └── evaluate.py
├── runtime_v2/
│   ├── models.py
│   ├── limits.py
│   ├── circuit_breaker.py
│   ├── retry.py
│   └── events.py
├── memory/
│   ├── service.py
│   ├── long_term.py
│   ├── medium_term.py
│   ├── short_term.py
│   ├── index.py
│   ├── retrieve.py
│   └── compact/
│       ├── turn.py
│       ├── session.py
│       └── memory.py
├── execution_units/
│   ├── models.py
│   ├── runner.py
│   ├── store.py
│   └── browser_worker.py
├── plugins/
│   ├── host.py
│   ├── manifest.py
│   ├── loader.py
│   └── recruit/
│       ├── manifest.py
│       ├── toolkit.py
│       ├── observation.py
│       ├── guard.py
│       ├── persona.py
│       └── router.py
├── mcp_v2/
│   ├── registry.py
│   ├── bridge.py
│   └── health.py
├── skills/
│   ├── registry.py
│   ├── executor.py
│   └── sandbox.py
├── evolution/
│   ├── learning_writer.py
│   ├── promotion.py
│   ├── queue.py
│   └── prompt_evolution.py
├── assistant/
│   ├── conversation.py
│   ├── stream.py
│   └── session_store.py
├── api/
│   ├── __init__.py
│   └── routers/
│       ├── agent.py
│       ├── assistant.py
│       ├── evolution.py
│       ├── recruit_agent.py
│       └── ...
└── server.py
```

---

## 4. 旧能力 → 新位置 映射表（必须逐项保留，不允许漏）

| 原表达 / 原位置 | 新位置 | 必须保留的语义 | 旧代码处理 |
|---|---|---|---|
| `services/context_assembler.py` 里 task/session/candidate/job/global fragment 组装 | `kernel/assemble.py` + `memory/index.py` + `memory/retrieve.py` + scenario fragments | 三书签思路、memory index、最近事件、按 policy 选 fragment | 吸收后删除旧文件 |
| `runtime/prompts.py` 的 Persona/Profile/Memory 拼装 | `kernel/assemble.py` + `PluginHost.collect_persona_fragments()` | base persona + overlay + fragment 组装 | 吸收后删除旧文件 |
| `runtime/agent_loop.py` 的 tool loop | `kernel/deliberate.py` | 内联 tool call 循环、tool_result 回灌、多轮迭代 | 吸收后删除旧文件 |
| `runtime/agent_loop.py` 的 waiting_human / replan / result submission | `kernel/deliberate.py` + `kernel/guard.py` + `kernel/evaluate.py` + `execution_units/` | wait_human、replan、终态提交 | execution_contract 脚手架删除 |
| `services/agent.py` 的 enqueue/run/follow-up | `agents/autonomous.py` + `agents/heartbeat.py` + repositories | tick 执行、follow-up、self-audit | 删除旧 service |
| `services/agent.py` 的 sourcing/progression/retry heuristics | `agents/heartbeat.py` + recruit pack policy | 自主 sourcing / progression / retry | 老 selector 型 orchestration 删除或下沉 |
| `services/runtime_control.py` 的 run/session/work_item 生命周期 | `agents/autonomous.py` + repo helper + runtime_v2 events | run 开始/结束、checkpoint、event、work item 对齐 | 删除旧文件 |
| `services/runtime.py` 的执行记录/episode/runtime 控制 | `execution_units/` + `runtime_v2/` + `evolution/` | 执行记录、trace、持久化 | 删除旧文件 |
| candidate takeover lock 混在核心逻辑中 | `plugins/recruit/` + `candidate_autonomous_locks` | take over / release / handover | 只允许在 recruit pack 中存在 |
| `take_over_candidate` / `release_candidate` / `list_locked_candidates` 被视作 core tools | `plugins/recruit/toolkit.py` | 三个工具全部保留 | 从 core 移出 |
| `human_locked` / `recent_handover` 在 core context 中硬编码 | `plugins/recruit/observation.py` | Observation 标注事实，不做过滤 | 从 core 移出 |
| 外部触达限制写成 core 逻辑 | `plugins/recruit/guard.py` + core `ToolSpec.external_target` | Assistant 外部动作前必须满足场景规则 | core 只保留元数据 |
| 人工接管 prompt 文案写在 core | `plugins/recruit/persona.py` | handover 理解、locked 候选人跳过规则 | 从 core 移出 |
| recruit intervention endpoint 混在通用 agent router | `plugins/recruit/router.py` 挂 `/api/recruit/...` | lock / release / list | 从 core router 移出 |
| Assistant cancel 缺失 | `agents/assistant.py` + `assistant/*` + `runtime_v2.models.CancellationToken` | `/cancel`、SSE 中断、partial outputs 持久化 | 新增，不能省略 |

**判定规则**：如果上述任意一行只做了“从旧位置删除”，但没有在新位置落地，则这次实现视为不完整。

---

## 5. 旧文件切断矩阵（Codex 必须逐个判断去留）

| 旧文件 | 当前职责 | 新目标位置 | 最终动作 |
|---|---|---|---|
| `services/agent.py` | orchestration 总控、run_once、autonomy sourcing/progression | `agents/autonomous.py` + `agents/heartbeat.py` + recruit pack policy | **删除** |
| `services/context_assembler.py` | context fragment 聚合 | `kernel/assemble.py` + `memory/*` | **删除** |
| `runtime/agent_loop.py` | LLM/tool loop | `kernel/deliberate.py` | **删除** |
| `runtime/prompts.py` | prompt 组装 | `kernel/assemble.py` + plugin persona fragments | **删除** |
| `services/autonomy.py` | autonomy loop poller | `agents/heartbeat.py` | **删除** |
| `services/runtime_control.py` | run/session/work_item/checkpoint lifecycle | `agents/autonomous.py` + repository helpers | **删除** |
| `services/runtime.py` | execution runtime / episode / trace 管理 | `execution_units/` + `runtime_v2/` + `evolution/` | **删除** |
| `api/routers/runtime.py` | execution/runtime API | `/api/agent` + `/api/assistant` + `/api/debug` + `/api/evolution` | **删除** |
| `api/routers/recruit_agent.py` | recruit-agent profile + memory + runtime surfaces | 仅保留 recruit-specific 装配/profile/memory 面 | **大幅瘦身** |
| `services/container.py` | 旧路径 composition root | 新 v2 container | **保留重写** |
| `server.py` | app bootstrap + old autonomy start | 新 heartbeat/autonomous/assistant bootstrap | **保留重写** |
| `runtime/tools.py` | tool registry + execution-plan helper tools | ToolBus v2 基础层 | **保留重构** |
| `runtime/providers.py` | provider 抽象 | provider 基础层 | **保留重构/复用** |
| `scheduler/queue.py` | queue persistence | Heartbeat/Autonomous 使用 | **保留扩展** |
| `scheduler/scheduler.py` | serial scheduling | 可复用或薄封装 | **保留扩展** |
| `src/recruit_agent/*` wrappers | 历史兼容包装 | 不需要 | **删除** |

---

## 6. 最终对外 API（本计划定义最终接口，Codex 无需再看 spec）

### 6.1 Autonomous / generic agent API

保留并实现：
- `GET /api/agent`
- `POST /api/agent/tasks`
- `POST /api/agent/run-once`
- `GET /api/agent/queue`
- `POST /api/agent/queue/recover`
- `GET /api/agent/runs?status=...`
- `GET /api/agent/runs/{run_id}`
- `GET /api/agent/runs/{run_id}/ticks`
- `GET /api/agent/runs/{run_id}/ticks/{tick_id}/turns`
- `POST /api/agent/assemblies/{jd_id}`（当前招聘实现仍由 recruit_agent router 暴露也可以，但最终必须保留该能力）
- `GET /api/agent/assemblies/{jd_id}/versions`
- `POST /api/agent/heartbeat/pause`
- `POST /api/agent/heartbeat/resume`
- `GET /api/agent/heartbeat/status`
- `POST /api/agent/autonomous/pause`
- `POST /api/agent/autonomous/resume`
- `GET /api/agent/autonomous/state`

### 6.2 Assistant API

必须实现：
- `POST /api/assistant/conversations`
- `GET /api/assistant/conversations?user_id=...`
- `GET /api/assistant/conversations/{id}`
- `DELETE /api/assistant/conversations/{id}`
- `POST /api/assistant/conversations/{id}/turn`（SSE）
- `POST /api/assistant/conversations/{id}/confirm`
- `POST /api/assistant/conversations/{id}/cancel`

SSE 事件至少包括：
- `turn_started`
- `llm_delta`
- `tool_call`
- `tool_result`
- `llm_final`
- `turn_completed`
- `turn_cancelled`
- `compacted`

### 6.3 Recruit pack API

必须挂载在 `/api/recruit/...`：
- `POST /api/recruit/candidates/{candidate_person_id}/lock`
- `POST /api/recruit/candidates/{candidate_person_id}/release`
- `GET /api/recruit/candidates/locks`

### 6.4 Evolution API

必须实现：
- `GET /api/evolution/queue?status=pending`
- `POST /api/evolution/queue/{id}/approve`
- `POST /api/evolution/queue/{id}/reject`
- `GET /api/evolution/skills?status=trial`
- `POST /api/evolution/skills/{id}/promote`

### 6.5 Debug / Observability API

至少实现：
- `GET /api/debug/runs/{run_id}/replay`
- `GET /api/debug/cache/stats`
- `GET /api/debug/mcp/health`
- `GET /api/debug/circuit-breakers`
- `GET /api/debug/alerts`

---

## 7. 最终数据模型（本计划只保留 Codex 必须实现的关键约束）

### 7.1 直接扩旧表，不建平行表

必须直接扩：
- `agent_runs`
- `approval_items`
- `agent_runtime_events`
- `candidate_person_memories`
- `job_description_memories`
- `agent_global_memories`
- `skills`
- `mcp_servers`
- `agent_learnings`
- `evolution_artifacts`

### 7.2 必须新增的新表

必须新增：
- `job_assemblies`
- `prompt_overlay_revisions`
- `agent_tick_records`
- `agent_turn_records`
- `tool_invocations`
- `conversation_sessions`
- `conversation_turns`
- `compaction_events`
- `agent_global_state`
- `candidate_autonomous_locks`（recruit pack）

### 7.3 关键字段约束

#### `agent_runs` 必须有
- `run_id`
- `agent_kind`
- `turns_count`
- `ticks_count`
- `prompt_tokens`
- `completion_tokens`
- `cache_hit_tokens`
- `escalate_reason`
- `lock_scope`
- `idempotency_key`
- `wakeup_state`
- `runtime_metadata['fairness_state']`

#### `approval_items` 必须有
- `run_pk`
- `tick_pk`
- `conversation_pk`
- `source_kind`
- `tool_name`
- `args_digest`
- `expires_at`
- `executed_at`
- `idempotency_key`

#### `agent_runtime_events` 必须有
- `tick_id`
- `turn_id`
- `conversation_id`
- `seq`

#### `conversation_turns` 必须有
- `turn_id`
- `tool_calls`
- `tool_results`
- `status`
- `cancel_reason`
- `cancelled_at`

#### `candidate_autonomous_locks` 必须有
- `candidate_person_id`
- `locked_at`
- `locked_by`
- `reason`
- `expires_at`
- `released_at`
- `released_by`
- `handover_note`
- `handover_next_hint`

### 7.4 memory 规则

- 不建统一 `memory_items`
- 继续使用三张 memory 表
- 扩成 item-row 语义
- 支持：
  - `memory_item_id`
  - `kind`
  - `index_name`
  - `index_description`
  - `confidence`
  - `evidence_refs`
  - `trust_level`
  - `version`
  - `supersedes_id`
  - `expires_at`
  - `item_metadata`

---

## 8. Kernel / Runtime 契约（Codex 必须按此实现）

### 8.1 Runtime 抽象

必须实现以下核心类型：
- `GoalRef`
- `CheckpointRef`
- `FairnessState`
- `Observation`
- `CacheBlock`
- `LLMRequest`
- `Deliberation`
- `GuardVerdict`
- `WakeupRequest`
- `ExecutionUnitResult`
- `Effects`
- `TickOutcome`
- `CancellationToken`
- `RuntimeLimits`

### 8.2 Observation 必须保持去招聘化

`Observation` 只能有：
- `world_snapshot`
- `scope_ref`
- `scope_kind`
- `recent_events`
- `available_tools`
- `available_skills`
- `available_mcps`
- `hash`

不能写：
- `jd`
- `candidate`
- `job_description`
- `candidate_lock`

这些只能由 scenario pack enricher 注入到 `world_snapshot` 里。

### 8.3 FairnessState 必须保持去招聘化

`FairnessState` 只能是：
- `last_scope_ref`
- `same_scope_ticks`
- `soft_limit`
- `hard_limit`
- `cooldown_until`

不能出现 `last_jd_id` / `same_jd_ticks`。

### 8.4 8 节点职责

#### Trigger
- 初始化 `TickContext`
- 创建 tick 记录起点

#### Sense
- 拉 coarse-grained world snapshot
- 拉 recent events
- 调用 `plugin_host.run_observation_enrichers()`
- 不能知道业务语义

#### Assemble
- 书签 1：base persona + tools + persona fragments
- 书签 2：assembly overlay + global memory index + scenario fragments
- 书签 3（可选）：scope-local memory / recent events
- 不允许把 recruit-specific 结构写死在 core assemble

#### Deliberate
- 是唯一允许执行内联 tool call 的节点
- tool result 必须回灌消息历史
- 高噪音网页动作下沉 execution unit

#### Guard
- preflight + final 两层
- preflight 必须支持 `plugin_host.run_guard_checks()`
- core 不知道具体 guard 的业务语义

#### Act
- 只落地副作用
- 不执行新的 tool_call

#### UpdateMemory
- 非 fatal 时写 learning
- 通过 `record_learning` 进入 evolution/promotion 流

#### Evaluate
- 产出 `continue / sleep / wait_human / complete / escalate`
- 不规定“围绕哪个业务对象推进”，由场景 policy 决定

### 8.5 Assistant turn 契约

Assistant 复用同一套骨架，但必须支持：
- conversation history / jsonl 作为会话事实源
- turn cancel
- recovery turn
- SSE 事件流
- turn-level compact / conversation-level compact

### 8.6 Execution Unit 契约

必须实现：
- `create_execution_unit`
- `wait_unit`
- `unit_result`

状态机必须是：
- `queued`
- `running`
- `blocked_human`
- `blocked_environment`
- `succeeded`
- `failed`
- `timed_out`
- `cancelled`

### 8.7 PluginHost 契约

必须支持注册：
- `register_tools(namespace, toolkit)`
- `register_observation_enricher(namespace, fn)`
- `register_guard_check(namespace, fn)`
- `register_persona_fragment(namespace, label, text)`
- `register_router(namespace, router)`

必须支持执行：
- `run_observation_enrichers()`
- `run_guard_checks()`
- `collect_persona_fragments()`

### 8.8 ToolBus 契约

Tool 元数据必须有：
- `category`
- `external_target`
- `resource_target_kind`

Tool 执行必须支持：
- async execute
- `cancel_token`
- plugin tools / core tools / skill tools / mcp tools 合并

### 8.9 recruit pack 契约

必须实现：
- `take_over_candidate`
- `release_candidate`
- `list_locked_candidates`
- Observation enrichers：`human_locked` / `lock_meta` / `recent_handover`
- Guard checks：
  - 被接管候选人禁止动作
  - Assistant 外部动作必须满足全局 pause 条件
- persona fragment：人工接管行为约定
- `/api/recruit/...` router

---

## 9. 测试与验收要求（Codex 必须执行）

### 9.1 自动化测试范围

必须跑：
- `python3 -m pytest services/backend/tests/agent_v2 -q`
- `python3 -m pytest services/backend/tests -q`
- `mypy --strict services/backend/src/scene_pilot/{agents,kernel,memory,evolution,skills,plugins,mcp_v2,assistant,runtime_v2}`

如 API/types 触及 desktop：
- `npm run desktop:typecheck`

### 9.2 必须补的测试类型

#### 单测
- runtime_v2 contracts
- PluginHost
- Kernel happy path
- Guard core
- Guard recruit pack
- Memory isolation/conflict
- Circuit breaker
- ExecutionUnit runner
- ToolBus v2

#### 集成测试
- tick end-to-end
- heartbeat self-audit
- assistant conversation
- recruit pack takeover flow
- recruit pack external action gate
- evolution pipeline

### 9.3 UI 测试说明

UI 不要求自动化完成。

但最终实现后必须满足：
- 后端 API 与前端类型至少可编译
- human 可以在监督下进行：
  - Assistant 对话流验证
  - recruit candidate lock/release 手工验证
  - runtime replay/debug 手工验证

这部分不阻塞 Codex 自动实现，但要在 plan 最后明确列为“人工验收项”。

---

## 10. 实施任务（Codex 逐项执行，不允许跳步）

### 任务 1：建立新目录骨架与测试骨架

**目标**：先建立 v2 目录树与 `tests/agent_v2/` 基础结构。

**文件：**
- 新建：`services/backend/src/scene_pilot/{agents,kernel,runtime_v2,memory,assistant,execution_units,plugins,plugins/recruit,mcp_v2,skills,evolution}/__init__.py`
- 新建：`services/backend/tests/agent_v2/unit/__init__.py`
- 新建：`services/backend/tests/agent_v2/integration/__init__.py`
- 新建：`services/backend/tests/agent_v2/unit/test_module_layout.py`

- [ ] 写失败测试：验证上述目录必须存在
- [ ] 跑：`python3 -m pytest services/backend/tests/agent_v2/unit/test_module_layout.py -q`
- [ ] 建目录和空包
- [ ] 再跑同一测试直到通过
- [ ] 提交：`refactor: scaffold agent v2 runtime packages`

### 任务 2：把 ORM / Repository 改造成最终 v2 数据模型

**目标**：一次性把重叠持久化结构改到最终形态，不建平行表。

**文件：**
- 修改：`services/backend/src/scene_pilot/models/domain.py`
- 修改：`services/backend/src/scene_pilot/repositories/domain.py`
- 修改：`services/backend/tests/test_db_migrations.py`
- 新建：`services/backend/tests/agent_v2/unit/test_domain_v2_contracts.py`

**必须落地：**
- 扩 `agent_runs`
- 扩 `approval_items`
- 扩 `agent_runtime_events`
- 扩三张 memory 表 item-row 语义
- 新增：`job_assemblies` / `prompt_overlay_revisions` / `agent_tick_records` / `agent_turn_records` / `tool_invocations` / `conversation_sessions` / `conversation_turns` / `compaction_events` / `agent_global_state` / `candidate_autonomous_locks`

- [ ] 先写失败测试，校验字段是否存在
- [ ] 跑：`python3 -m pytest services/backend/tests/agent_v2/unit/test_domain_v2_contracts.py services/backend/tests/test_db_migrations.py -q`
- [ ] 修改 ORM 与 repo helper
- [ ] 再跑测试直到通过
- [ ] 提交：`refactor: reshape persisted models for agent v2`

### 任务 3：建立 runtime_v2 基础契约

**目标**：建立所有核心 dataclass / typed contracts / limits / breaker / retry。

**文件：**
- 新建：`runtime_v2/models.py`
- 新建：`runtime_v2/limits.py`
- 新建：`runtime_v2/events.py`
- 新建：`runtime_v2/circuit_breaker.py`
- 新建：`runtime_v2/retry.py`
- 新建：`services/backend/tests/agent_v2/unit/test_runtime_v2_models.py`
- 新建：`services/backend/tests/agent_v2/unit/test_circuit_breaker.py`

**必须实现：**
- `GoalRef`
- `CheckpointRef`
- `FairnessState`
- `Observation`
- `CacheBlock`
- `LLMRequest`
- `Deliberation`
- `GuardVerdict`
- `WakeupRequest`
- `ExecutionUnitResult`
- `Effects`
- `TickOutcome`
- `CancellationToken`
- `RuntimeLimits`

- [ ] 先写失败测试
- [ ] 跑：`python3 -m pytest services/backend/tests/agent_v2/unit/test_runtime_v2_models.py services/backend/tests/agent_v2/unit/test_circuit_breaker.py -q`
- [ ] 实现 contracts 与 breaker/retry
- [ ] 再跑直到通过
- [ ] 提交：`refactor: add agent v2 runtime contracts`

### 任务 4：建立 PluginHost 扩展面

**目标**：把 PluginHost 变成 Kernel 唯一场景挂载面。

**文件：**
- 新建：`plugins/host.py`
- 新建：`plugins/manifest.py`
- 新建：`plugins/loader.py`
- 新建：`services/backend/tests/agent_v2/unit/test_plugin_host.py`

**必须实现：**
- `register_tools`
- `register_observation_enricher`
- `register_guard_check`
- `register_persona_fragment`
- `register_router`
- `run_observation_enrichers`
- `run_guard_checks`
- `collect_persona_fragments`
- `install(host)` manifest 协议

- [ ] 写失败测试
- [ ] 跑：`python3 -m pytest services/backend/tests/agent_v2/unit/test_plugin_host.py -q`
- [ ] 实现 host/loader/manifest
- [ ] 再跑直到通过
- [ ] 提交：`refactor: add plugin host extension surface`

### 任务 5：实现 MemoryService 与 item-row memory 子系统

**目标**：在现有三张 memory 表之上实现 v2 MemoryService。

**文件：**
- 新建：`memory/service.py`
- 新建：`memory/long_term.py`
- 新建：`memory/medium_term.py`
- 新建：`memory/short_term.py`
- 新建：`memory/index.py`
- 新建：`memory/retrieve.py`
- 新建：`services/backend/tests/agent_v2/unit/test_memory_isolation.py`
- 新建：`services/backend/tests/agent_v2/unit/test_memory_conflict.py`

**必须实现：**
- `index_for_scope`
- `read`
- `write(expected_version=...)`
- `search_semantic`
- `fetch_session_summary`
- `fetch_run_context`
- `set_run_context`
- `fetch_recent_events`

- [ ] 写失败测试
- [ ] 跑：`python3 -m pytest services/backend/tests/agent_v2/unit/test_memory_isolation.py services/backend/tests/agent_v2/unit/test_memory_conflict.py -q`
- [ ] 实现 MemoryService
- [ ] 再跑直到通过
- [ ] 提交：`refactor: add item-row memory service`

### 任务 6：把 runtime/tools.py 改造成 ToolBus v2 基础层

**目标**：保留可复用 provider/tool 机制，但去掉旧 execution-plan 专用味道。

**文件：**
- 修改：`runtime/tools.py`
- 修改：`runtime/providers.py`（如需要）
- 新建：`tools_v2/__init__.py`
- 新建：`tools_v2/read_memory.py`
- 新建：`tools_v2/record_learning.py`
- 新建：`tools_v2/enqueue_follow_up.py`
- 新建：`tools_v2/schedule_self_wakeup.py`
- 新建：`tools_v2/invoke_skill.py`
- 新建：`services/backend/tests/agent_v2/unit/test_toolbus_v2.py`

**必须实现：**
- tool metadata: `category` / `external_target` / `resource_target_kind`
- execute 支持 `cancel_token`
- core tools + plugin tools + skill tools + MCP tools 合并
- 删除不再使用的 execution-plan helper metadata

- [ ] 写失败测试
- [ ] 跑：`python3 -m pytest services/backend/tests/agent_v2/unit/test_toolbus_v2.py -q`
- [ ] 实现 ToolBus v2
- [ ] 再跑直到通过
- [ ] 提交：`refactor: reshape tool registry into v2 toolbus`

### 任务 7：实现 Kernel 八节点并移除旧 agent loop/context assembler/prompt path

**目标**：真正形成共享 Kernel。

**文件：**
- 新建：`kernel/kernel.py`
- 新建：`kernel/sense.py`
- 新建：`kernel/assemble.py`
- 新建：`kernel/deliberate.py`
- 新建：`kernel/guard.py`
- 新建：`kernel/act.py`
- 新建：`kernel/update_memory.py`
- 新建：`kernel/evaluate.py`
- 删除：`runtime/agent_loop.py`
- 删除：`runtime/prompts.py`
- 删除：`services/context_assembler.py`
- 新建：`services/backend/tests/agent_v2/unit/test_kernel_happy_path.py`

**必须实现：**
- Sense 粗快照 + enrichers
- Assemble 三书签 + persona fragments
- Deliberate 内联 tool loop
- Guard preflight/final 双层
- Act 落副作用
- UpdateMemory 写 learning
- Evaluate 产出 tick outcome

- [ ] 写失败测试
- [ ] 跑：`python3 -m pytest services/backend/tests/agent_v2/unit/test_kernel_happy_path.py -q`
- [ ] 实现八节点与 shared kernel
- [ ] 删除旧 `runtime/agent_loop.py` / `runtime/prompts.py` / `services/context_assembler.py`
- [ ] 再跑直到通过
- [ ] 提交：`refactor: replace legacy runtime loop with agent v2 kernel`

### 任务 8：实现 AutonomousAgent / Heartbeat，并删除旧 autonomy/orchestration/service 层

**目标**：用新的 Autonomous 路径替换 `services/agent.py` / `services/autonomy.py` / `services/runtime_control.py` / `services/runtime.py`。

**文件：**
- 新建：`agents/autonomous.py`
- 新建：`agents/heartbeat.py`
- 新建：`agents/assembly.py`
- 删除：`services/agent.py`
- 删除：`services/autonomy.py`
- 删除：`services/runtime_control.py`
- 删除：`services/runtime.py`
- 新建：`services/backend/tests/agent_v2/integration/test_heartbeat.py`
- 新建：`services/backend/tests/agent_v2/integration/test_tick_end_to_end.py`

**必须实现：**
- `run_tick_from_envelope`
- self-audit tick
- global pause 读取
- stale recovery
- run/tick/turn 持久化生命周期

- [ ] 写失败测试
- [ ] 跑：`python3 -m pytest services/backend/tests/agent_v2/integration/test_heartbeat.py services/backend/tests/agent_v2/integration/test_tick_end_to_end.py -q`
- [ ] 实现 Autonomous/Heartbeat
- [ ] 删除旧 services
- [ ] 再跑直到通过
- [ ] 提交：`refactor: replace legacy autonomy services with autonomous agent`

### 任务 9：实现 recruit Scenario Capability Pack，确保招聘能力没有被删而是被迁移

**目标**：把所有 recruit-only 能力完整迁入 `plugins/recruit/`。

**文件：**
- 新建：`plugins/recruit/manifest.py`
- 新建：`plugins/recruit/toolkit.py`
- 新建：`plugins/recruit/observation.py`
- 新建：`plugins/recruit/guard.py`
- 新建：`plugins/recruit/persona.py`
- 新建：`plugins/recruit/router.py`
- 修改：`models/domain.py`
- 修改：`repositories/domain.py`
- 新建：`services/backend/tests/agent_v2/integration/test_recruit_pack_takeover_flow.py`
- 新建：`services/backend/tests/agent_v2/integration/test_recruit_pack_external_action_gate.py`

**必须实现：**
- `candidate_autonomous_locks`
- `take_over_candidate`
- `release_candidate`
- `list_locked_candidates`
- `human_locked`
- `recent_handover`
- takeover guard
- external action + pause guard
- recruit persona fragment
- `/api/recruit/...` router

- [ ] 写失败测试
- [ ] 跑：`python3 -m pytest services/backend/tests/agent_v2/integration/test_recruit_pack_takeover_flow.py services/backend/tests/agent_v2/integration/test_recruit_pack_external_action_gate.py -q`
- [ ] 实现 recruit pack 全套
- [ ] 再跑直到通过
- [ ] 提交：`feat: add recruit scenario capability pack`

### 任务 10：实现 AssistantAgent、conversation 持久化、SSE、turn cancel

**目标**：让 Assistant 成为第二个共享 Kernel 的 agent。

**文件：**
- 新建：`assistant/conversation.py`
- 新建：`assistant/stream.py`
- 新建：`assistant/session_store.py`
- 新建：`agents/assistant.py`
- 新建：`api/routers/assistant.py`
- 新建：`services/backend/tests/agent_v2/integration/test_assistant_conversation.py`

**必须实现：**
- `conversation_sessions` / `conversation_turns`
- jsonl 事实源
- SSE 事件流
- `/cancel`
- `CancellationToken`
- recovery turn
- turn compact / conversation compact

- [ ] 写失败测试
- [ ] 跑：`python3 -m pytest services/backend/tests/agent_v2/integration/test_assistant_conversation.py -q`
- [ ] 实现 Assistant 全套
- [ ] 再跑直到通过
- [ ] 提交：`feat: add assistant agent and conversation runtime`

### 任务 11：实现 Execution Units

**目标**：把高噪音网页动作从主线剥离成显式执行单元。

**文件：**
- 新建：`execution_units/models.py`
- 新建：`execution_units/store.py`
- 新建：`execution_units/runner.py`
- 新建：`execution_units/browser_worker.py`
- 新建：`services/backend/tests/agent_v2/unit/test_execution_unit_runner.py`

**必须实现：**
- `create_execution_unit`
- `wait_unit`
- `unit_result`
- 状态机：queued/running/blocked_human/blocked_environment/succeeded/failed/timed_out/cancelled
- cooldown 语义

- [ ] 写失败测试
- [ ] 跑：`python3 -m pytest services/backend/tests/agent_v2/unit/test_execution_unit_runner.py -q`
- [ ] 实现 execution_units
- [ ] 再跑直到通过
- [ ] 提交：`feat: add execution unit subsystem`

### 任务 12：实现 Skills / Evolution / mcp_v2

**目标**：补齐 self-learning / trial / promotion / MCP v2 生态。

**文件：**
- 新建：`skills/registry.py`
- 新建：`skills/executor.py`
- 新建：`skills/sandbox.py`
- 新建：`evolution/learning_writer.py`
- 新建：`evolution/promotion.py`
- 新建：`evolution/queue.py`
- 新建：`evolution/prompt_evolution.py`
- 新建：`mcp_v2/registry.py`
- 新建：`mcp_v2/bridge.py`
- 新建：`mcp_v2/health.py`
- 新建：`api/routers/evolution.py`
- 新建：`services/backend/tests/agent_v2/integration/test_evolution_pipeline.py`

**必须实现：**
- `record_learning(promote=true)` 自动晋升或进入队列
- skill trial / active 流
- prompt_overlay revision / trial 指标
- mcp_v2 注册、桥接、健康检查、熔断

- [ ] 写失败测试
- [ ] 跑：`python3 -m pytest services/backend/tests/agent_v2/integration/test_evolution_pipeline.py -q`
- [ ] 实现 skills/evolution/mcp_v2
- [ ] 再跑直到通过
- [ ] 提交：`feat: add evolution skills and mcp v2 subsystems`

### 任务 13：重建 container / server / API wiring

**目标**：把 app bootstrap、container、router 全部切到新架构。

**文件：**
- 修改：`services/container.py`
- 修改：`server.py`
- 修改：`api/__init__.py`
- 修改：`api/routers/agent.py`
- 修改：`api/routers/recruit_agent.py`
- 删除：`api/routers/runtime.py`
- 删除：`src/recruit_agent/server.py`
- 删除：`src/recruit_agent/core/app.py`
- 修改：`services/backend/tests/test_api_app.py`

**必须实现：**
- container 构建：providers / ToolBus / PluginHost / MemoryService / agents / heartbeat / assistant / evolution / execution units / mcp_v2
- app 注册：assistant/evolution/recruit 路由
- `/api/agent` 成为 generic autonomous control surface
- `recruit_agent.py` 瘦身为 recruit-specific profile/assembly/memory surfaces

- [ ] 写失败测试
- [ ] 跑：`python3 -m pytest services/backend/tests/test_api_app.py -q`
- [ ] 重写 wiring
- [ ] 删除旧 router/wrapper
- [ ] 再跑直到通过
- [ ] 提交：`refactor: rewire backend around agent v2 runtime`

### 任务 14：重写旧测试面，形成最终测试体系

**目标**：去掉所有旧 runtime 假设测试，形成 `tests/agent_v2/` 为主的最终测试集。

**文件：**
- 删除：`services/backend/tests/test_runtime_agent_loop.py`
- 删除：`services/backend/tests/test_runtime_prompts.py`
- 删除：`services/backend/tests/test_runtime_tools.py`
- 删除：`services/backend/tests/test_api_runtime.py`
- 重写或删除：`services/backend/tests/test_autonomy_loop.py`
- 重写或删除：`services/backend/tests/test_api_recruit_agent.py`
- 修改：`services/backend/tests/test_api_app.py`
- 扩充：`services/backend/tests/agent_v2/**`

- [ ] 写失败 smoke test，验证旧 runtime 测试文件已删除
- [ ] 跑：`python3 -m pytest services/backend/tests/agent_v2/unit/test_final_cutover_cleanup.py -q`
- [ ] 删除旧测试，补全新测试
- [ ] 跑：`python3 -m pytest services/backend/tests/agent_v2 -q`
- [ ] 提交：`test: replace legacy runtime tests with agent v2 suite`

### 任务 15：最终清理、全流程自动化验证、手动 UI 验收准备

**目标**：确保旧代码已删光，新架构是唯一真相源，并完成自动化验收；UI 留给人工监督阶段。

**文件：**
- 修改：`CLAUDE.md`
- 如有必要修改：后端相关文档索引
- 修改：`apps/desktop/src/lib/api.ts`（仅在 API 改动导致前端 typecheck 失败时）
- 修改：`apps/desktop/src/lib/types.ts`（同上）

**必须完成：**
- 删除所有剩余旧 runtime dead code
- 全量 backend pytest 通过
- 新模块 strict mypy 通过
- 如触及前端 API/type，desktop typecheck 通过
- 形成手工 UI 验收 checklist

- [ ] 写失败 dead-code inventory 测试
- [ ] 跑：`python3 -m pytest services/backend/tests/agent_v2/unit/test_final_cutover_cleanup.py -q`
- [ ] 删除最后残留的旧文件/旧分支
- [ ] 运行完整自动化验证：

```bash
python3 -m pytest services/backend/tests -q && \
mypy --strict services/backend/src/scene_pilot/{agents,kernel,memory,evolution,skills,plugins,mcp_v2,assistant,runtime_v2}
```

- [ ] 若触及前端 API/types，再运行：

```bash
npm run desktop:typecheck
```

- [ ] 产出人工 UI 验收 checklist（写在 commit message 或最终总结中即可，不要求再写新 md）
- [ ] 提交：`refactor: complete agent v2 direct cutover`

---

## 11. 人工 UI 验收 checklist（Codex 不自动执行，但必须准备）

实现完成后，human 需要手动验证：

1. Assistant 基础对话是否可正常流式输出
2. Assistant 在 tool_call 后是否能正确显示 pending confirmation
3. Assistant `/cancel` 后是否停止流并保留 partial outputs
4. Autonomous pause / resume 是否真实生效
5. recruit candidate lock / release / handover 是否按预期工作
6. debug replay 是否能完整看到 run/tick/turn/tool
7. desktop UI 是否还能打开主要页面，不出现明显 API 崩溃

---

## 12. Codex 最终交付标准

只有同时满足以下条件，才算这次实施完成：

- 新 runtime 是唯一运行路径
- 旧 runtime/orchestration 代码已删除
- Kernel 中没有 recruit-first 语义污染
- recruit 能力完整保留在 Scenario Capability Pack
- 自动化 backend tests 全绿
- strict mypy 全绿
- 如触及前端类型/API，desktop typecheck 全绿
- 代码结构与本计划一致，不再需要额外阅读 `agent-v2-implementation-spec.md` 或 `agent-v2-design-summary.md`

---

## 13. 计划自检

### 13.1 覆盖性
本计划已经显式覆盖：
- Kernel 纯粹性
- Autonomous/Assistant 双 agent
- 8 节点契约
- Memory / Compact / Evolution / PluginHost / MCP / ExecutionUnit / Assistant cancel
- recruit capability pack
- API 重建
- 旧代码删除
- 全流程测试
- UI 手动验收边界

### 13.2 不再依赖外部文档
Codex 不需要再读：
- `docs/agent-v2-implementation-spec.md`
- `docs/agent-v2-design-summary.md`

因为本计划已经把：
- 目标结构
- 契约边界
- API
- 数据模型
- 迁移映射
- 删除策略
- 测试策略
- 任务顺序
全部重新整理在同一份文档中。

### 13.3 最后要求
Codex 执行本计划时：
- 遇到可自行判断的问题，直接做最符合本计划的实现
- 不要为了“稳妥”保留旧代码
- 不要为了“兼容”留下双路径
- 不要为了“减少 diff”弱化架构切换
- 以最终清晰、纯粹、单一路径为第一优先级
