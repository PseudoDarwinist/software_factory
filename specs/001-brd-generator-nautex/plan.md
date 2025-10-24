# Implementation Plan: BRD/PRD Block Editor & Content Pipeline

**Branch**: `001-brd-generator-nautex` | **Date**: 2025-09-07 | **Spec**: /Users/chetansingh/Documents/AI_Project/Software_Factory/specs/001-brd-generator-nautex/spec.md
**Input**: Feature specification from `/specs/001-brd-generator-nautex/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
4. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
5. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, or `GEMINI.md` for Gemini CLI).
6. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
7. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
8. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Primary requirement: Present AI-generated PRD/BRD as clean, editable, block-based documents with collapsible sections and diagram rendering—never exposing raw JSON to users. Technical approach: Define a single AI interchange (Markdown profile with fenced diagrams or structured Blocks JSON), normalize to a canonical Block Document with stable IDs via a library + CLI, and render blocks in the editor with robust type detection, outline/deep-link support, and graceful fallbacks.

## Technical Context
**Language/Version**: TypeScript (frontend), Python 3.11 (backend)  
**Primary Dependencies**: React, diagram renderer (Mermaid profile), markdown/blocks normalizer (library to be created), Flask/Socket.IO existing gateway  
**Storage**: PostgreSQL (existing) for document versions; local draft cache in browser  
**Testing**: Jest/Vitest (frontend contracts), pytest (backend contracts/integration)  
**Target Platform**: Modern web (Chrome/Edge/Safari current stable)  
**Project Type**: web (frontend + backend)  
**Performance Goals**: p95 open-to-interactive ≤ 1500ms for typical docs; progressive render for long docs  
**Constraints**: No raw JSON in UI; diagrams must render or show friendly errors; deep links stable  
**Scale/Scope**: Target 300–500 blocks, 10–20 diagrams per doc (confirm)

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Simplicity**:
- Projects: 3 (api, cli, tests)
- Using framework directly? Yes (React directly, minimal wrappers)
- Single data model? Yes (Block Document), DTO only if export differs
- Avoiding patterns? Yes (no Repository/UoW; small pure functions for normalize)

**Architecture**:
- EVERY feature as library? Yes → `sf-blocks` (normalize/validate/render helpers)
- Libraries listed: `sf-blocks` (purpose: parse/normalize/validate, CLI), `sf-diagrams` (optional renderer adapters)
- CLI per library: `sf-blocks normalize --in <path|-> --out <path|-> --format json|text --strict` (help/version provided)
- Library docs: llms.txt planned alongside library and CLI usage examples

**Testing (NON-NEGOTIABLE)**:
- RED-GREEN-Refactor enforced: yes (contract tests before implementation)
- Commits show tests first: yes (gate in PR checklist)
- Order: Contract→Integration→E2E→Unit strictly followed
- Real dependencies used? Yes (render to real DOM in FE tests; real parse & real Postgres for save path integration)
- Integration tests for: new libraries, contract changes, shared schemas: yes
- FORBIDDEN: Implementation before test, skipping RED phase

**Observability**:
- Structured logging included: yes (load/parse/normalize/render/save with trace_id)
- Frontend logs → backend stream: yes (bridge existing Socket.IO)
- Error context sufficient: yes (block id, type, operation)

**Versioning**:
- Version number assigned: `sf-blocks` 0.1.0 (BUILD increments each change)
- Breaking changes handled: deprecations + dual-run compatibility tests
- Migration plan documented with each contract change

## Project Structure

### Documentation (this feature)
```
specs/001-brd-generator-nautex/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
backend/
├── src/
│   ├── api/
│   ├── services/
│   └── models/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

lib/
└── sf-blocks/           # library + CLI (normalize/validate)
```

**Structure Decision**: Web application (frontend + backend) with a shared library `sf-blocks` for normalization/validation and CLI exposure.

## Phase 0: Outline & Research
1. Extract unknowns from Technical Context above:
   - Interchange choice [NEEDS CLARIFICATION]: Markdown profile vs structured Blocks JSON
   - Diagram fences & capabilities: flow/class/sequence subset and error reporting
   - Performance targets and lazy-loading strategy for 300–500 blocks
   - Accessibility targets (keyboard, ARIA) and outline/deep-link UX
   - Autosave/debounce semantics and versioning granularity
   - Export/import mapping, including diagrams and callouts
2. Generate and dispatch research tasks:
   - For each unknown: "Research {unknown} for BRD/PRD editor pipeline"
   - For each technology choice: "Best practices for block editors and diagram rendering in web apps"
3. Consolidate findings in `research.md` using format:
   - Decision, Rationale, Alternatives considered

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. Extract entities from feature spec → `data-model.md`:
   - Document, Block (id/type/content/children/order/parent), Version, Outline
2. Generate API/CLI contracts from functional requirements → `contracts/`:
   - CLI: `sf-blocks normalize` (stdin|file) → Block Document JSON schema
   - REST: GET `/api/docs/{id}/blocks`, PUT `/api/docs/{id}/blocks` (idempotent), error envelopes
3. Generate contract tests from contracts (listed in plan; written during build):
   - CLI round-trip tests (markdown→blocks→markdown)
   - REST schema validation tests
4. Extract test scenarios from user stories → `quickstart.md`:
   - Open PRD path renders blocks, diagrams render or show friendly errors, deep-link navigation
5. Update agent file incrementally:
   - Run `softwarefactory/scripts/update-agent-context.sh claude` after plan is saved

**Output**: data-model.md, /contracts/*, quickstart.md (tests authored in build phase)

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Each contract → contract test task [P]
- Each entity → model creation task [P]
- Each user story → integration test task
- Implementation tasks to make tests pass

**Ordering Strategy**:
- TDD order: Tests before implementation
- Dependency order: Models before services before UI
- Mark [P] for parallel execution (independent files)

**Estimated Output**: 25-30 numbered, ordered tasks in tasks.md

