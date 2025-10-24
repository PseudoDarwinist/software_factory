# Software Factory

Build software like a factory: capture ideas, generate specs, plan work, implement with AI, and validate — all in a real-time, event‑driven system.

Mission Control brings visibility and flow. The AI Broker and agents bring speed and consistency. Redis and Postgres keep everything coherent and auditable.

![Mission Control](mission-control/artifacts/screenshot.webp)

## Table of Contents

- Background
- The Workflow
- What Makes This Different?
- System Architecture
- Workflow Phases
- API & Command Quickstart
- Parallel Execution
- Key Features & Benefits
- Example Flow
- Get Started
- Technical Notes
- Support

## Background

Teams lose time to context drift, serial work, and hidden progress. Software Factory enforces spec‑driven delivery and observable flow.

- Context persists: PRDs/specs/tasks and events form an audit trail.
- Work runs in parallel: agents and humans collaborate without collisions.
- Progress is visible: Mission Control presents the state in real-time.

## The Workflow

```mermaid
graph LR
  A[Think] --> B[Define]
  B --> C[Plan]
  C --> D[Build]
  D --> E[Validate]
```

## What Makes This Different?

- Spec‑first delivery: every change maps to requirements/design/tasks.
- Live event fabric: Redis pub/sub + WebSockets stream the truth to UI.
- BYO assistants: Claude/Goose/Model Garden via AI Broker + MCP tools.
- Traceability: Postgres event log and artifact models for compliance.

## System Architecture

See the high‑contrast diagram:

`docs/diagrams/system_architecture.mmd`

Key components:

- `src/app.py`: Unified Flask app, blueprints, services, and Socket.IO.
- `src/services/event_bus.py`: Redis‑backed pub/sub and fan‑out.
- `src/services/websocket_server.py`: Authenticated, project‑scoped broadcasts.
- `src/services/ai_broker.py`: Model selection, queuing, context enrichment.
- `src/services/spec_generation_service.py`: Async Define agent orchestration.
- `src/services/claude_code_task_service.py`: Git workspace + PR automation.
- `src/services/vector_service.py`: Embeddings + semantic search (pgVector fallback to text search).
- `src/models/*`: SQLAlchemy models for tasks, artifacts, events, projects, runs.

## Workflow Phases

1) Think — Ideas captured from Slack or uploads appear instantly.
2) Define — AI drafts requirements/design/tasks; artifacts move AI‑Draft → Reviewed → Frozen.
3) Plan — Tasks parsed and prioritized; Kanban with dependencies.
4) Build — Agents create branches, implement, open PRs; reviews via GitHub.
5) Validate — PR merges trigger validation runs and phase transitions.

## API & Command Quickstart

API (selected):

- System: `GET /api/status`, `GET /api/system/health`
- Stages: `POST /api/idea/:id/move-stage`, `GET /api/specification/:id`
- Tasks: `GET /api/tasks`, `POST /api/tasks/:id/start`, `POST /api/tasks/:id/approve`
- Webhooks: `POST /api/webhooks/github`, `POST /api/webhooks/slack`

Local dev:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d  # Postgres + Redis
export DATABASE_URL=postgresql://sf_user:sf_password@localhost/software_factory
export REDIS_URL=redis://localhost:6379/0
python -m src.app
# open http://localhost:8000
```

Docker:

```bash
docker compose up --build
# app on http://localhost:8000
```

## Parallel Execution

Tasks aren’t atomic. A single issue fans out across: DB changes, API endpoints, UI components, tests, and docs. Agents and humans can run in parallel because:

- Workspaces isolate branches per task.
- Webhooks + WS synchronize status without chat‑log archaeology.
- The event log preserves every transition.

## Key Features & Benefits

- Real‑time Mission Control: instant stage/task updates and presence.
- AI orchestration: model selection, vector context, and guardrails.
- Spec lifecycle: AI‑Draft → Reviewed → Frozen with badges.
- GitHub native: branches, PRs, reviews, validation on merge.
- Observability: Prometheus metrics, audit events, health API.

## Example Flow

```bash
# Move idea to Define (UI calls API)
POST /api/idea/{ideaId}/move-stage { targetStage: "define", projectId }

# Spec generation runs async; requirements/design/tasks artifacts appear

# Start a task in Build
POST /api/tasks/{taskId}/start { agentId: "ui-api-agent" }

# GitHub webhooks update status; approve task to merge PR
POST /api/tasks/{taskId}/approve { approvedBy: "alice" }
```

## Get Started

Prereqs:

- Python 3.11+
- Docker (for Postgres/Redis)
- Node (to build Mission Control, if needed)

Setup:

1. Copy `.env.example` to `.env`; set `DATABASE_URL`, `REDIS_URL`, optional `GITHUB_TOKEN`.
2. `pip install -r requirements.txt`
3. `docker compose up -d`
4. `python -m src.app`

## Technical Notes

- Vector Search: Uses all‑MiniLM‑L6‑v2; automatic fallback to text search if pgVector UDFs absent.
- WebSockets: Socket.IO (gevent) with JWT auth and project‑scoped filtering.
- AI Broker: Guardrails skip vector context when analyzing documents/PRDs to reduce hallucination.
- Migrations: `flask db` via Flask‑Migrate; create tables on startup for dev.

## Support

Issues and feature requests are welcome. If this helps your team, consider ⭐ the repo and sharing feedback.

