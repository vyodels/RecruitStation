# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Product direction

- This repo is for **Recruit Agent**, a local-first recruiting workspace.
- The current product surface is recruit-agent-first: candidate progress, candidate/job/global memory, communication review, playbook evolution, and skill governance.
- Legacy execution/runtime structures still exist, but they are implementation machinery rather than the main user-facing product model.

## Repository shape

- `apps/desktop`: Electron + React desktop app. Renderer code lives in `src/`; Electron boot/preload code lives in `electron/`.
- `packages/shared`: shared TypeScript contracts, especially workflow/status/state-machine definitions used across the desktop app.
- `services/backend`: FastAPI backend with SQLite persistence, agent/runtime services, approvals, MCP integration, scheduler, sync, and autonomy loops.
- `docs/` and `Plan.md`: product direction, release, and refactor context.

## Setup and common commands

### Frontend / desktop

```bash
npm install --ignore-scripts
npm run desktop:dev
npm run desktop:build
npm run desktop:typecheck
npm run shared:build
```

### Desktop packaging

```bash
npm run desktop:release:prepare
npm run desktop:release:preflight
npm run desktop:package:dir
npm run desktop:package
```

For distribution-grade macOS packaging, see `docs/macos-release.md`.

### Backend setup

Backend requires Python `>=3.14`.

```bash
cd services/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### Backend development

```bash
uvicorn recruit_agent.server:create_app --reload --factory
```

The desktop app expects the backend at `RECRUIT_AGENT_BACKEND_URL` or `http://127.0.0.1:8741` by default.

### Tests

```bash
# full backend suite from repo root
npm run backend:test
python3 -m pytest services/backend/tests -q

# full backend suite from services/backend
python3 -m pytest

# single backend test file
python3 -m pytest services/backend/tests/test_api_app.py -q

# targeted backend test selection
python3 -m pytest services/backend/tests/test_api_app.py -k health -q
```

There is currently no unified ESLint, Prettier, or Ruff configuration in this repo, and no frontend test runner is configured in `apps/desktop`. The minimum automated verification is usually `npm run desktop:typecheck` plus the relevant `pytest` command.

Root `.npmrc` sets `ignore-scripts=true`; keep using `npm install --ignore-scripts` unless you explicitly need packaging-time install scripts.

## Architecture notes

- **Desktop boot flow:** `apps/desktop/electron/main.ts` starts the backend first, waits for `/health`, then loads the renderer. In packaged builds it prefers a bundled backend binary; in source mode it falls back to `python3 -m recruit_agent.server`.
- **Renderer/backend boundary:** `apps/desktop/src/lib/api.ts` is the main desktop API client. The renderer talks directly to backend HTTP APIs and subscribes to `/ws/agent-stream` for live agent events.
- **Shared contracts are partial:** canonical shared workflow/status/state-machine types live in `packages/shared/src/contracts.ts`, `packages/shared/src/types/stateMachine.ts`, and `packages/shared/src/data/defaultStateMachine.ts`, but many richer desktop-facing records still live in `apps/desktop/src/lib/types.ts`.
- **Backend package naming is mixed on purpose:** implementation lives under `services/backend/src/scene_pilot`, while public entrypoints also expose `recruit_agent.server`.
- **Backend composition is container-driven:** `scene_pilot.server:create_app` builds an `AppContainer` that wires settings, SQLAlchemy engine/session setup, feature flags, provider registry (Anthropic and OpenAI-compatible), tool registry, scheduler, event stream, MCP registry, sync services, dashboard services, and agent control.
- **Persistence is local-first:** the backend initializes SQLite-backed persistence on startup and recovers queued tasks / runtime records through container-managed services.
- **Prompt boundaries matter:** natural-language agent behavior should live under `services/backend/src/scene_pilot/prompts/`. Prefer changing prompt files, structured context, tool contracts, or skills before changing core runtime logic.

## Repo-specific working rules

- If you touch `apps/desktop`, read `apps/desktop/DESIGN_GUIDELINES.md` first. It is a **visual/layout system**, not a content template; do not copy example fields, labels, or counts directly into product UI.
- When desktop and backend truly share a contract, prefer moving it into `packages/shared` instead of duplicating similar types.
- Do not patch model capability gaps by hardcoding site-specific rules, page vocabularies, selectors, or one-off workflows into the core runtime/agent path. Fix those through prompts, tool boundaries, structured context, or skills instead.
- Backend configuration is loaded from environment variables with the `RECRUIT_AGENT_` prefix.
