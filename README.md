# Recruit Agent

Recruit Agent is a local-first recruiting automation workspace.

The current direction is no longer the earlier execution console model. The product now centers on a built-in recruiting agent with editable workflow, isolated memory, skill governance, candidate progress tracking, and operator-controlled communication review.

## Product Focus

Current scope:

- one primary built-in `Recruit Agent`
- candidate pipeline and progress tracking
- candidate-isolated memory and JD-isolated memory
- editable agent profile, prompt, role, boundaries, and compression policies
- editable recruiting workflow with patch-based evolution
- structured skills with user management and review
- chat-like candidate communication review
- local-first persistence with optional later-stage intranet upload

Not the current product focus:

- generic runtime productization
- execution-record-first operations
- fixed backlog of site integrations

## Core Objects

- `RecruitAgentProfile`: agent identity, prompt assets, tone, boundaries, success criteria, forbidden actions, compression policies
- `RecruitAgentWorkflow`: recruiting workflow graph used internally by the agent
- `Candidate`: structured candidate record and progress source of truth
- `Candidate Memory`: long-term memory isolated per candidate
- `Job / JD Memory`: long-term memory isolated per JD
- `Agent Global Memory`: reusable global recruiting strategy memory
- `Skill`: structured capability unit with metadata, health, and governance
- `Candidate Thread`: runtime communication and confirmation thread for one candidate

## Current Repository Layout

- `apps/desktop`: Electron + React desktop app
- `services/backend`: FastAPI backend, SQLite persistence, agent execution, approvals, sync scaffolding
- `packages/shared`: shared frontend contracts and mock/demo data
- `docs`: handoff and release notes

## Current Refactor Direction

The codebase still contains legacy execution structures from the earlier architecture phase. They are being retained as implementation machinery, but the product surface is moving to a recruit-agent-first model:

- workflow becomes the agent’s internal playbook
- execution records remain technical artifacts, not the main user-facing object
- candidate progress, memory, communication, and evolution governance become the primary UI surfaces

See [Plan.md](./Plan.md) for the active implementation plan.

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

## Packaging

For local desktop verification:

```bash
npm run desktop:release:prepare
npm run desktop:release:preflight
npm run desktop:package:dir
```

For distribution-grade macOS packaging, see [docs/macos-release.md](./docs/macos-release.md).
