# Recruit Agent

Recruit Agent is a local-first recruiting automation workspace.

The current direction is no longer the earlier execution console model. The product now centers on two built-in agents, `Assistant` and `Autonomous`, managed through a desktop ChatOverlay alongside the recruiting workspace, with editable execution blueprints, isolated memory, skill governance, candidate progress tracking, and operator-controlled communication review.

## Product Focus

Current scope:

- two built-in agents: `Assistant` and `Autonomous`
- candidate pipeline and progress tracking
- candidate-isolated memory and JD-isolated memory
- editable agent profile, prompt, role, boundaries, and compression policies
- editable recruiting playbook with patch-based evolution
- structured skills with user management and review
- chat-like candidate communication review
- desktop `home / candidates / settings` plus an `Agents` overlay entry as the primary user-facing shell
- local-first persistence with optional later-stage intranet upload

Not the current product focus:

- generic runtime productization
- execution-record-first operations
- fixed backlog of site integrations

## Core Objects

- `RecruitAgentProfile`: agent identity, prompt assets, tone, boundaries, success criteria, forbidden actions, compression policies
- `RecruitAgentPlaybook`: recruiting playbook graph used internally by the agent
- `Candidate`: structured candidate record and progress source of truth
- `Candidate Memory`: long-term memory isolated per candidate
- `Job / JD Memory`: long-term memory isolated per JD
- `Agent Global Memory`: reusable global recruiting strategy memory
- `Skill`: structured capability unit with metadata, health, and governance
- `Candidate Thread`: runtime communication and confirmation thread for one candidate

## Agent Runtime Architecture

The agent runtime is organised around `InteractionEngine`. Autonomous and Assistant provide product-specific lifecycle, persistence, and UI/API surfaces; the engine owns the LLM transcript, provider invocation, tool loop, tool result feedback, permission boundary, and runtime outputs.

```
┌──────────────────────────────────────────────────────────────────────┐
│  Product Agents  (AutonomousAgent / AssistantAgent)                  │
│  ─────────────────────────────────────────                           │
│  Own: run/session records, SSE stream, approval materialization,     │
│       scheduling, business memory, user-visible status               │
│                                                                      │
│  ┌── one turn lifecycle ─────────────────────────────────────────┐   │
│  │  InteractionEngine.submitMessage(input)                       │   │
│  │    → LLMRequest / LLMResponse                                 │   │
│  │    → tool call / tool result feedback loop                    │   │
│  │    → permission_requested / turn_completed / turn_failed      │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

### Terminology anchor

- `turn` uses the Codex semantic: one complete LLM-driven cycle from a trigger (user message, scheduler wake, run continuation) until the next point where a human must intervene.
- `InteractionEngine` is the runtime owner; `InteractionOutput` is the outbound stream/envelope emitted while a turn runs. There is no standalone `interaction` runtime primitive.
- `tick` is **not used** anywhere in this project.

### Layer responsibilities

| Layer | Knows | Does not know |
|-------|-------|---------------|
| `InteractionEngine` | provider, transcript, tool schemas, tool execution, permission requests, runtime outputs | database, HTTP, SSE, scheduler, user identity, product-specific run/session status |
| Product agents | when to trigger, when to stop, how to persist, how to stream, how to cancel, how to surface approval/recovery | provider protocol details and tool feedback loop internals |

### Ownership of grey-area concerns

| Concern | Owner | Why |
|---------|-------|-----|
| Tool execution | `InteractionEngine` through canonical `ToolDefinition` handlers | engine-internal feedback loop |
| Tool approval / permission | `InteractionEngine` emits `permission_requested`; product agents materialize approvals and resume approved tool calls as transcript state | engine owns the boundary, product agents own the human workflow |
| Memory read / write | Product agents and runtime tools | memory is business/product state, not engine state |
| Turn record, SSE stream, run record | Product agents | lifecycle and persistence are product concerns |
| Cancel coordination | Product agents call `InteractionEngine.interrupt()`; provider and tool workers observe cancellation where supported | cancellation is cooperative and best-effort |
| Turn-level safety budget | Product agents pass engine budgets explicitly | defaults are chosen by product context |
| Scheduler fairness, scope cooldown | AutonomousAgent | cross-turn scheduling |
| Human confirmation flow | Product agents | only the product layer knows how to notify and resume a human-gated flow |

### One-line summary

- `InteractionEngine` is the single runtime mechanism for LLM/tool turns.
- Autonomous and Assistant differ in trigger, persistence, memory, approvals, and UI/API expression, not in a separate runtime loop.

## Current Repository Layout

- `apps/desktop`: Electron + React desktop app with `home / candidates / settings` as top-level sections and an `Agents` ChatOverlay for dual-agent lifecycle work
- `services/backend`: FastAPI backend, SQLite persistence, agent execution, approvals, sync scaffolding
- `packages/shared`: shared frontend contracts and mock/demo data
- `docs`: current specs, runtime design, active plans, guides, release notes, and archived historical material

## Current Refactor Direction

The Agent runtime refactor has moved to the new architecture:

- `agent_runtime/**` is business-agnostic Agent core
- recruiting business logic lives in product adapters, tools, skills, plugins, prompts, MCP capabilities, and business services
- `Assistant` and `Autonomous` are product-layer Agent shapes over the shared runtime
- candidate progress, memory, communication, and evolution governance are product/business surfaces, not runtime concepts

Long-term rules live in [`docs/specs/`](./docs/specs/). Agent runtime design lives in [`docs/design/agent-core/`](./docs/design/agent-core/). Active implementation plans live in [`docs/plan/active/`](./docs/plan/active/). Historical material lives under `docs/archive/` and `docs/plan/archive/`.

## Development

Frontend:

```bash
npm install --ignore-scripts
npm run desktop:dev
```

Backend:

```bash
cd services/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn recruit_agent.server:create_app --reload --factory
```

Tests:

```bash
python3 -m pytest services/backend/tests -q
npm run desktop:typecheck
```

Runtime terminology and schema note:

- 本次 Agent runtime 术语与表结构收敛直接改了本地 SQLite 的表名与字段名，不保留兼容层。升级后如果本地数据库来自旧版本，请删除旧的 workspace SQLite 文件后再启动后端，让新模型直接重建。

## Packaging

For local desktop verification:

```bash
npm run desktop:release:prepare
npm run desktop:release:preflight
npm run desktop:package:dir
```

For distribution-grade macOS packaging, see [docs/macos-release.md](./docs/macos-release.md).
