# Software Factory Constitution

## Core Principles

### I. Library‑First, Contract‑Driven
- Every capability starts as a standalone library with a single, explicit purpose and clear docs (no organizational or “grab‑bag” libraries).
- Libraries are independently testable, releasable, and documented (“llms.txt” style notes required alongside code).
- Application layers (API, UI, agents) consume libraries; app code must be thin adapters around stable contracts.

### II. Text‑First CLI Interface
- Every library exposes a CLI command with text I/O: args/stdin → stdout; errors → stderr.
- Support `--format` for `json|text`, `--help`, `--version`, and deterministic exit codes.
- CLIs double as the primary contract surface for agents and integration tests; REST endpoints are allowed but not a substitute for the CLI.

### III. Test‑First (NON‑NEGOTIABLE)
- Red‑Green‑Refactor is mandatory: write tests → approve → see them fail → implement → refactor.
- Test order of precedence: Contract → Integration → E2E → Unit (no implementation before failing tests exist).
- Prefer real dependencies over mocks at boundaries (Postgres, Redis, HTTP) to ensure fidelity of contracts.

### IV. Integration Testing Triggers
- Require integration tests when: creating a new library, changing any public contract, adding inter‑service communication, or touching shared schemas/events.
- Integration tests must run against real services or faithful local equivalents (e.g., Postgres, Redis, Slack/GitHub adapters in safe mode).
- Contract tests validate text I/O (CLI and REST) and event envelopes.

### V. Observability By Default
- Structured logs to stdout/stderr with `trace_id`, `project_id`, and actor metadata; consistent JSON schema for machine reads.
- Multi‑tier log streaming: frontend → backend → central stream; include error context and breadcrumbs.
- Emit metrics for queue lengths, latencies, and failure rates; capture minimal PII and redact secrets.

### VI. Versioning & Breaking Changes
- Use `MAJOR.MINOR.BUILD` for all libraries and contracts; increment BUILD on any change, MINOR for new non‑breaking features, MAJOR for breaking changes.
- Breaking changes require: deprecation window, dual‑run or compatibility tests, and a documented migration plan.
- Keep a `MIGRATION.md` and update examples/tests together in the same change.

### VII. Radical Simplicity (YAGNI)
- Max three projects per feature by default (e.g., `api`, `cli`, `tests`) to keep scope small.
- Use frameworks directly; avoid wrappers and heavyweight patterns (Repository, UoW, global singletons) unless proven necessary.
- Prefer a single data model; only introduce DTOs when serialization requirements differ.

## Platform Constraints & Standards

- Event‑Driven Architecture with Redis pub/sub/streams and a Flask/WS gateway; Postgres is the system of record; optional pgVector for semantic context.
- Standard event envelope includes `id`, `type`, `trace_id`, timestamps, and normalized payloads; all agents must preserve `trace_id`.
- Stages and artifacts: Think → Define → Plan → Build → Validate; spec artifacts progress through AI Draft → Human Reviewed → Frozen and are versioned.
- MCP interoperability: expose tools via the local MCP server for context, drafting, and artifact persistence. External assistants must use text I/O contracts.
- Security: JWT auth with role scoping; audit logs for sensitive actions; never log secrets; follow least‑privilege for tokens and webhooks.
- Performance budgets are explicit in specs/plans (p95 latency, memory, throughput) and enforced with tests where relevant.

## Development Workflow & Quality Gates

- Spec‑driven flow: Define produces `requirements.md`, `design.md`, and `tasks.md` artifacts; Planner parses tasks; Build executes under TDD.
- Plans and tasks must pass the Constitution Check sections in `softwarefactory/templates/plan-template.md` and `softwarefactory/templates/tasks-template.md`.
- Contract files and CLI flags are treated as public API; any change must update tests, docs, and version numbers in lock‑step.
- Observability and versioning are checked as first‑class gates during Plan and Task generation.
- Frontend and backend logs are correlated by `trace_id`; E2E tests assert logs/metrics emit for happy‑path and failure scenarios.

## Governance

- This Constitution supersedes other practices. All PRs must include a compliance checklist and justification for any complexity introduced.
- Amendments require: updated version number, migration guidance, and synchronization of templates and command docs.
- Runtime development guidance for agents lives in `CLAUDE.md`; keep it aligned when this document changes.
- Source of truth for this file: `softwarefactory/memory/constitution.md` (commands must reference this path).

**Version**: 2.2.0 | **Ratified**: 2025-06-13 | **Last Amended**: 2025-09-07
