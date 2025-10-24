# Research – BRD/PRD Block Editor & Content Pipeline

Date: 2025-09-07
Owner: 001-brd-generator-nautex

## Interchange Format
- Decision: Use a Markdown Profile (PRD‑MP 1.0) as the AI interchange; normalize to an internal Block Document JSON.
- Rationale: Human‑readable, resilient to minor format drift, easy to author and diff; avoids brittle JSON parsing from LLMs.
- Alternatives considered: Direct structured Blocks JSON (precise but fragile to LLM drift); HTML (rich but harder to map to editable blocks); ProseMirror/Slate ops (too low‑level for LLMs).
- Key conventions:
  - Front‑matter (YAML) for: title, version, authors, tags.
  - Headings: `#`, `##`, `###` become heading_1..3 blocks.
  - Callouts: `> [!NOTE]`, `> [!WARNING]` -> callout blocks with severity.
  - Checklists: `- [ ]` / `- [x]` -> checklist_item blocks.
  - Collapsible sections: `::: details Title` ... `:::` -> toggle block with children.
  - Diagrams: fenced code blocks with info string:
    - ```mermaid flow
      ...syntax...
      ```
    - Variants: `mermaid class`, `mermaid sequence`.

## Normalization Rules
- Decision: Canonical Block Document with stable `id`, `type`, `content`, `children[]`, `order_index`, `parent_id`.
- ID generation: hash of (`type`, canonicalized text, parent lineage) with short prefix `b_`; collisions resolve by suffix `~n`.
- Deep links: `#b-<id>`; headings retain slug alias for human‑friendly anchors.
- Outline: computed from headings and toggle titles; persisted in document metadata.
- Round‑trip: Blocks → PRD‑MP Markdown → Blocks must be lossless for supported types.

## Diagram Rendering
- Decision: Support Mermaid profile for flow/class/sequence with strict fences.
- Rationale: Mature, portable syntax; widely adopted; deterministic render.
- Error handling: Inline error panel with line/column; preserve raw code for edits; never show raw JSON.

## Performance & UX
- Decision: p95 open‑to‑interactive ≤ 1500ms for ≤ 400 blocks.
- Strategies: parse in Web Worker; virtualized list rendering; progressive diagram hydration; lazy image loading; save debounced at 1500ms idle.

## Accessibility
- Decision: Keyboard navigation across blocks (ArrowUp/Down, Enter/Shift+Enter, Alt+Arrow for move), ARIA roles for tree/regions, sufficient contrast.
- Rationale: Notion‑like productivity for all users; compliance and usability.

## Versioning & Persistence
- Decision: Persist original PRD‑MP and normalized Block Document; version each save with author, timestamp, diff summary.
- Rationale: Provenance retained; safe rollbacks; audit trail.

## Observability
- Decision: Emit structured logs with `trace_id`, `doc_id`, `block_id`, `operation` (`load|parse|normalize|render|save|error`).
- Rationale: Rapid diagnosis of pipeline issues.

## Open Questions (minor)
- Table support scope (sorting, column types) – default simple Markdown tables.
- Image upload limits and transformations – default pass‑through.

All major NEEDS CLARIFICATION items are resolved for Phase 1.

