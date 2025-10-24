# Data Model – BRD/PRD Block Editor

## Entities

### Document
- id: string
- title: string
- version: string (semver-like for doc revisions)
- created_at: datetime
- updated_at: datetime
- author: string
- blocks: Block[] (root-level ordered)
- outline: OutlineIndex[]
- original_interchange: string (PRD‑MP markdown)
- metadata: object

### Block
- id: string (stable)
- type: enum (heading_1, heading_2, heading_3, paragraph, bulleted_list, numbered_list, checklist_item, quote, callout, code, diagram, table, toggle, image, link, reference)
- content: object (type‑specific)
- children: Block[] (ordered)
- order_index: number
- parent_id: string | null
- collapsed: boolean (toggle‑only)
- annotations: object

### OutlineIndex
- id: string (block id)
- title: string
- level: number (1–3)
- href: string (deep link anchor)

## Block Content Schemas (selected)
- heading: { text: string }
- paragraph: { text: string, marks?: InlineMark[] }
- list item: { text: string }
- checklist_item: { text: string, checked: boolean }
- callout: { text: string, tone: "note"|"warning"|"tip" }
- code: { language: string, code: string }
- diagram: { dialect: "mermaid", kind: "flow"|"class"|"sequence", code: string }
- toggle: { title: string }
- table: { rows: string[][] }
- image: { src: string, alt?: string }

## Invariants
- Block IDs are unique and stable across edits to unrelated blocks.
- Parent/child relationships form a valid tree (no cycles).
- Outline derived from headings/toggles must match existing blocks.

