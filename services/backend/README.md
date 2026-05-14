# RecruitStation Backend

FastAPI backend foundation for the RecruitStation workspace.

## What is here

- SQLAlchemy models for candidates, recruit-station profiles, playbooks, skills, approvals, settings, audit logs, and agent learning records.
- Repository layer for local-first SQLite persistence.
- Pydantic schemas for REST payloads.
- FastAPI routers for health, dashboard, recruit-station, recruit-station execution, candidates, skills, settings, approvals, sync, and metrics.

## Run

Install dependencies and start the app:

```bash
python -m pip install -e .[dev]
recruit-station-backend --port 8741
```

By default the backend stores SQLite data under the configured data directory and exposes the API on `127.0.0.1`.

## API surface

- `GET /health`
- `GET|POST|PATCH|DELETE /api/recruit-station/playbooks`
- `GET|POST /api/recruit-station/execution/*`
- `GET|POST|PATCH|DELETE /api/candidates`
- `GET|POST|PATCH|DELETE /api/skills`
- `GET|PUT /api/settings`
- `GET|POST|PATCH /api/approvals`
- `GET /api/metrics`
