# CLAUDE_cn.md

本文件是 `CLAUDE.md` 的中文对照版，便于阅读理解；默认给 Claude Code 使用的仍然是根目录下的 `CLAUDE.md`。

## 产品方向

- 本仓库对应的产品是 **Recruit Agent**，一个 local-first 的招聘工作台。
- 当前产品主线是 recruit-agent-first：候选人进度、候选人 / JD / 全局 memory、候选人沟通审核、playbook 演进、skill 治理。
- 早期的 execution / runtime 结构仍然保留，但更多是实现层 machinery，而不是主要的用户产品模型。

## 仓库结构概览

- `apps/desktop`：Electron + React 桌面端。渲染层代码在 `src/`，Electron 启动与 preload 代码在 `electron/`。
- `packages/shared`：共享 TypeScript 契约，尤其是桌面端会复用的 workflow / status / state-machine 定义。
- `services/backend`：FastAPI 后端，包含 SQLite 持久化、agent/runtime 服务、审批、MCP 集成、scheduler、sync 和 autonomy loop。
- `docs/` 与 `Plan.md`：产品方向、发布与重构上下文。

## 初始化与常用命令

### 前端 / 桌面端

```bash
npm install --ignore-scripts
npm run desktop:dev
npm run desktop:build
npm run desktop:typecheck
npm run shared:build
```

### 桌面端打包

```bash
npm run desktop:release:prepare
npm run desktop:release:preflight
npm run desktop:package:dir
npm run desktop:package
```

如果要做 distribution-grade 的 macOS 打包，查看 `docs/macos-release.md`。

### 后端初始化

后端要求 Python `>=3.14`。

```bash
cd services/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### 后端开发启动

```bash
uvicorn recruit_agent.server:create_app --reload --factory
```

桌面端默认会连接 `RECRUIT_AGENT_BACKEND_URL`，如果未设置则使用 `http://127.0.0.1:8741`。

### 测试

```bash
# 在仓库根目录跑完整后端测试
npm run backend:test
python3 -m pytest services/backend/tests -q

# 在 services/backend 目录内跑完整后端测试
python3 -m pytest

# 跑单个后端测试文件
python3 -m pytest services/backend/tests/test_api_app.py -q

# 按关键字筛选目标后端测试
python3 -m pytest services/backend/tests/test_api_app.py -k health -q
```

当前仓库没有统一的 ESLint、Prettier 或 Ruff 配置，`apps/desktop` 也没有配置 frontend test runner。通常最低限度的自动化验证是 `npm run desktop:typecheck` 加上相关的 `pytest` 命令。

根目录 `.npmrc` 设置了 `ignore-scripts=true`；除非你明确需要打包阶段的 install script，否则继续使用 `npm install --ignore-scripts`。

## 架构说明

- **桌面端启动链路：** `apps/desktop/electron/main.ts` 会先启动后端，等待 `/health` 成功后再加载 renderer。打包后优先使用 bundled backend binary；源码模式下回退到 `python3 -m recruit_agent.server`。
- **Renderer / backend 边界：** `apps/desktop/src/lib/api.ts` 是桌面端主 API client。renderer 直接调用后端 HTTP API，并通过 `/ws/agent-stream` 订阅实时 agent 事件。
- **共享契约并不完整：** 核心共享的 workflow / status / state-machine 类型主要在 `packages/shared/src/contracts.ts`、`packages/shared/src/types/stateMachine.ts`、`packages/shared/src/data/defaultStateMachine.ts`，但很多更丰富的桌面端 record 仍然定义在 `apps/desktop/src/lib/types.ts`。
- **后端包命名是混合的：** 主要实现位于 `services/backend/src/scene_pilot`，但对外入口同时暴露 `recruit_agent.server`。
- **后端采用容器化组装：** `scene_pilot.server:create_app` 会构建 `AppContainer`，统一装配 settings、SQLAlchemy engine / session、feature flags、provider registry（Anthropic 与 OpenAI-compatible）、tool registry、scheduler、event stream、MCP registry、sync service、dashboard service 与 agent control。
- **持久化是 local-first：** 后端启动时会初始化 SQLite 持久化，并通过容器管理的服务恢复遗留队列任务与 runtime 记录。
- **prompt 边界很重要：** 面向 agent 的自然语言行为约束应放在 `services/backend/src/scene_pilot/prompts/` 下。优先修改 prompt 文件、结构化上下文、tool contract 或 skill，而不是把站点/场景特化逻辑塞进 core runtime。

## 仓库特有工作规则

- 如果修改 `apps/desktop`，先读 `apps/desktop/DESIGN_GUIDELINES.md`。它是**视觉与布局规范**，不是内容模板；不要把里面示例字段、文案或数量直接复制到真实产品页面。
- 如果桌面端与后端确实共享同一份契约，优先把它放进 `packages/shared`，不要维护两份相似类型。
- 不要通过在 core runtime / agent 主路径里硬编码站点规则、页面词表、选择器或一次性 workflow 来弥补模型能力缺口。应优先通过 prompts、tool boundaries、结构化上下文或 skills 解决。
- 后端配置通过 `RECRUIT_AGENT_` 前缀的环境变量加载。
