# Agent 架构设计（Agent Kernel + Agent Assembly + Turn / Round Model）

> Status: archived
> Supersedes: -
> Superseded by: docs/plan/archive/agent-v2-design-summary.md; docs/plan/archive/2026-04-19-agent-v2-direct-cutover-plan.md
> Distilled into: partial: docs/specs/2026-04-20-dual-agent-product-architecture.md
> Last reviewed against code: 2026-04-20
> Legacy path retained: docs/agent架构设计.md

> 这份文档记录本轮讨论里最重要的一次架构纠偏：
> Autonomous Agent 和 Assistant Agent 的差异，不应该建模为“两套不同的 agent 架构”，
> 而应该建模为“同一个 Agent Kernel，在不同 prompt、context、tool、memory、policy、wakeup 配置下的两种装配结果”。

---

## 1. 核心结论

**Agent 架构本身应该统一。**

Autonomous Agent 和 Assistant Agent **不是两套不同架构**，而是同一个 Agent Kernel，在不同的：

- `prompt`
- `context assembly`
- `tool set`
- `memory view`
- `policy`
- `wakeup / session mode`

配置下运行出来的两种形态。

也就是说，不应该是：

```text
Autonomous Agent 架构 ≠ Assistant Agent 架构
```

而应该是：

```text
Agent Kernel
  + Prompt Profile
  + Context Profile
  + Tool Profile
  + Memory Profile
  + Policy Profile
  + Wakeup / Session Profile
= 某一种 agent 形态
```

---

## 2. Agent 不能决定自己是否“通用”

Agent Kernel 只提供能力：

- 怎么调用 LLM
- 怎么组装 system / user / tool context
- 怎么读 memory
- 怎么执行 tools / skills
- 怎么处理 approvals
- 怎么保存事件、结果、压缩摘要

它本身不知道自己是：

- Autonomous Agent
- Assistant Agent
- 还是以后别的 agent

这些都应该是**装配结果**，不是 Kernel 的硬编码分支。

---

## 3. 真正决定 agent 行为差异的 6 个 Profile

### 3.1 Prompt Profile

定义 agent 的角色、目标、原则、语气、长期行为约束。

#### Autonomous Agent 示例
- 持续补人、评分、同步、联系
- 偏自治
- 关注长期目标和持续运行

#### Assistant Agent 示例
- 响应 human 请求
- 偏任务完成
- 关注本轮对话意图

---

### 3.2 Context Profile

定义每次调用 LLM 时，哪些上下文会被装进去、怎么装、优先级如何。

#### Autonomous Agent 示例
- 当前 Observation 快照
- memory index
- 最近事件摘要
- 不保留长历史对话

#### Assistant Agent 示例
- 历史对话
- 用户当前指令
- 相关 memory
- 可读 Autonomous Agent 的高层状态

---

### 3.3 Tool Profile

定义允许看到和调用哪些 tools / skills / adapters。

#### Autonomous Agent 示例
- search / score / sync / outreach / parse / skill-creator

#### Assistant Agent 示例
- 查询、汇总、解释、分析
- 必要时也能调重型 worker 或 skill
- 但默认不一定全自动执行

---

### 3.4 Memory Profile

定义 agent 能看到哪些 memory、如何检索、是否允许写入。

#### Autonomous Agent 示例
- 能读写 GlobalMemory / CandidateMemory / JobMemory
- 偏业务执行记忆

#### Assistant Agent 示例
- 能读用户偏好、项目记忆、Loop 的高层策略摘要
- 默认不直接接管 Loop 的内部执行细节记忆

---

### 3.5 Policy Profile

定义权限、审批、自动执行边界、skill 生效策略。

#### 示例
- 默认中间型权限
- 可配置权限范围
- skill draft 可自动生成
- 是否自动应用由 policy 决定
- 审批可以静默 / 半自动 / 全审批

---

### 3.6 Wakeup / Session Profile

定义 agent 是怎么被唤醒和持续运行的。

#### Autonomous Agent 示例
- wakeup by timer / event / manual start
- 一直运行
- 可 sleep / pause / resume

#### Assistant Agent 示例
- wakeup by human message
- 会话驱动
- 有 chat session / summary / compaction

---

## 4. 正确设计图

不该是“两个不同架构”，而应该是：

```text
                Agent Kernel
  ┌────────────────────────────────────────────────────┐
  │ LLM invocation                                     │
  │ context assembler                                  │
  │ tool/skill execution                               │
  │ memory retrieval                                   │
  │ policy / approval                                  │
  │ event logging / result persistence                 │
  │ summary / compaction                               │
  └────────────────────────────────────────────────────┘
                     ↑                     ↑
                     │                     │
       ┌─────────────┘                     └─────────────┐
       │                                                 │
Autonomous Agent Assembly                               Assistant Agent Assembly
- prompt profile                                  - prompt profile
- context profile                                 - context profile
- tool profile                                    - tool profile
- memory profile                                  - memory profile
- policy profile                                  - policy profile
- wakeup profile                                  - session profile
```

---

## 5. 正确的讨论焦点

之前比较容易掉进的误区是：

- Autonomous Agent 一套架构
- Assistant Agent 再来一套架构
- 再去争论“哪个更通用”

但正确焦点应该是：

### 不是比较“架构是否通用”
而是比较：

#### 方案 1：统一 Kernel + 差异化装配
这是当前最符合需求的方向。

#### 方案 2：按 agent 类型拆 Kernel
这是不希望走的方向。

所以更准确的原则应该写成：

> **Agent 的差异不是 Kernel 结构差异，而是装配差异。**

---

## 6. 对当前代码意味着什么

### 6.1 不应该做的

- 为 Autonomous Agent 单独做一套执行内核
- 为 Assistant Agent 再做另一套执行内核
- 在 Kernel 层写死“这是 loop / 这是 assistant”

### 6.2 应该做的

在 Kernel 上层加一个 **Agent Assembly Layer**：

```text
AgentDefinition / AgentProfile
  - prompt_profile
  - context_profile
  - tool_profile
  - memory_profile
  - policy_profile
  - wakeup_profile
```

然后：

- `autonomous_agent` = 一个 assembly
- `assistant_agent` = 另一个 assembly

---

## 7. 这对 Skill 设计也有直接影响

之前已经明确：

> skill 颗粒度需要控制，不能拆得太碎

这也说明：

**skill 不是某个 agent 专属能力**，而是 Kernel 上可挂载的能力资产。

到底谁能看到、谁能调用，应该由：

- `tool profile`
- `policy profile`
- `prompt profile`

共同决定，而不是 skill 自己决定。

换句话说：

- skill 是资产
- agent assembly 决定是否挂载这项资产
- policy 决定能否自动执行 / 是否审批

---

## 8. Turn / Round Model

Autonomous Agent 和 Assistant Agent 在**单次执行骨架**上应该一致，但要明确拆成两层：

- 外层是 Driver 持有的 `turn`
- 内层是 `AgentKernel.run_round()` 驱动的 `round`

这里不应该再保留旧的单层执行骨架表述。区别不在骨架本身，而在：
- 触发输入不同
- 装配结果不同
- turn 出口状态不同

### Unified Turn / Round 表

| 层级 | 节点 | 作用 | Owner | 内部细节映射 |
|---|---|---|---|---|
| **Turn** | **Trigger / Wakeup** | 触发一次 turn | Driver | 定时器、事件、用户消息、sleep 到期 |
| **Turn** | **Resolve Assembly** | 加载本次 turn 的 Agent Assembly | Driver | 读取 `Prompt Profile / Context Profile / Tool Profile / Memory Profile / Policy Profile / Wakeup/Session Profile` |
| **Round** | **Sense** | 收集当前输入与现实状态 | `AgentKernel.run_round()` | 用户输入、Observation、事件、历史反馈、运行状态 |
| **Round** | **Assemble Request** | 把上下文组装成一次完整请求 | `AgentKernel.run_round()` | `system = 稳定 prompt/规则/记忆索引`；`user = 动态状态/当前任务/事件/历史摘要`；`tools = tool schema` |
| **Round** | **Deliberate** | 发起一次模型往返并接收输出 | `AgentKernel.run_round()` | OpenAI / Anthropic 请求发出，模型返回文本、结构化决策、tool call |
| **Round** | **Guard / Policy Check** | 对 assistant 的动作进行守卫 | `AgentKernel.run_round()` | 逐轮 preflight 检查权限、审批、预算、频率、幂等、安全边界 |
| **Round** | **Act** | 持久化副作用 | `AgentKernel.run_round()` | 写 DB、入队 follow-up、调度 wakeup、落事件/审批记录 |
| **Round** | **Update Memory** | 写入长期/中期产物 | `AgentKernel.run_round()` | 事件日志、执行摘要、memory 更新、plan state、skill draft、compaction 产物 |
| **Round** | **Evaluate** | 产出 `RoundOutcome` | `AgentKernel.run_round()` | 判断本轮是否推进目标，给出 `continue / wait_human / complete / escalate` 等信号 |
| **Turn** | **Continue / Sleep / Respond / Escalate** | 决定 turn 的出口 | Driver | Autonomous：continue / sleep / wait_event / pause_human；Assistant：respond / ask_follow_up / wait_user / approval（human confirm 后必须开启新的 recovery turn） |

一个 turn 内可以包含多轮 round；Kernel 只负责把一轮 `round` 跑完，是否继续下一轮由 Driver 决定。

---

## 9. Turn / Round 中 Context 的内部组成

`Update Context` 这一步建议固定拆成：

```text
Context =
  Background
+ Current Input
+ World State Summary
+ History
+ Memory Index
+ Memory Detail (on demand)
+ Plan State
+ Tool / Skill Availability
+ Policy Constraints
```

### 各部分含义

#### Background
长期稳定的信息：
- persona
- 长期目标
- 长期 prompt 约束
- 稳定业务原则

#### Current Input
本轮直接触发输入：
- 用户消息
- 定时触发原因
- 外部事件通知

#### World State Summary
当前真实状态快照：
- 结构化 DB 查询结果
- runtime 状态
- 外部环境状态

#### History
历史记录，但不一定总是长对话：
- Autonomous Agent：最近事件摘要 / 上轮执行摘要
- Assistant Agent：会话历史 / summary / recent turns

#### Memory Index
记忆索引元数据：
- 哪些 memory 可能相关
- 每条 memory 的 hook / preview

#### Memory Detail
只有在判断“相关”后才取：
- 某个候选人的详细记忆
- 某条策略的详细版本
- 某个 skill 的详细执行提示

#### Plan State
当前计划状态：
- 当前目标
- 子目标
- 当前阶段
- 已完成 / 待完成
- sleep / resume 条件

#### Tool / Skill Availability
本轮可见能力：
- 哪些 tool 能用
- 哪些 skill 挂载了
- 哪些外部能力失效了

#### Policy Constraints
本轮行动边界：
- 哪些动作可自动执行
- 哪些需要审批
- 是否允许静默应用 skill
- budget / rate / concurrency 限制

---

## 10. Turn / Round 中与 LLM 直接交互的内层链路

在外层 `turn` 里，真正和 LLM 发生直接往返的是每一轮 `round` 的下面这条链路：

```text
Assemble Request
→ Call LLM
→ Assistant Turn
→ Guard / Policy Check
→ Act
→ Observe
→ Re-enter Loop（如需要）
```

### 各节点含义

#### Assemble Request
组装本次 LLM 请求：
- system
- user/messages
- tools

#### Call LLM
发出一次 LLM API 请求。

#### Deliberate
接收模型输出：
- 文本
- 结构化决策
- tool call

#### Guard / Policy Check
如果 assistant 想调用 tool，不代表就能直接执行。
这里要检查：
- 权限是否允许
- 是否需要审批
- 是否超预算
- 是否违反频率限制
- 是否会重复执行
- 是否存在高风险副作用

#### Act
真正执行动作：
- 调 tool
- 调 skill
- 调 worker
- 修改业务数据

#### Observe
读取动作结果：
- tool result
- error
- side effect summary
- status transition
- artifact output

#### Re-enter Round
如果还没得到最终结论，Driver 会带着新增的 `tool_result` 和更新后的历史再次发起下一轮 `run_round()`。

所以：

> 一个 `turn` 内部包含多轮 `assistant → tool → assistant` 的往返是正常的；那是多轮 `round`，不是另一层新的顶级执行单元。

---

## 11. 对后续正式设计的影响

接下来正式设计时，不再用“Loop 架构 / Assistant 架构”来表述。

而应该改成：

## Agent Kernel + Two Assemblies + One Turn / Round Model

也就是：

- 一个统一 Kernel
- 两套装配：
  - `autonomous_agent_assembly`
  - `assistant_agent_assembly`
- 一个统一的外层 `turn` + 内层 `round` 模型

更准确的说法不是：
- `Autonomous Agent turn loop`
- `Assistant Agent turn loop`

而是：
- `Autonomous Agent Assembly on the shared turn/round model`
- `Assistant Agent Assembly on the shared turn/round model`

这才符合当前讨论里最重要的纠偏方向。

---

## 12. 一句话总结

**Agent Kernel 负责能力；Prompt / Context / Tools / Memory / Policy / Wakeup 负责塑造 agent。**

因此：

- Autonomous Agent 和 Assistant Agent 的不同，主要是装配不同
- 它们在单次执行骨架上共享同一个 turn / round 模型
- 差异来自装配输入，而不是 Kernel 架构不同
- 也不是“agent 自己决定自己是否通用”

这应该成为后续 Autonomous Agent / Assistant Agent 正式设计的第一原则。
