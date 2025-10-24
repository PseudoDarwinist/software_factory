# Quickstart – Validating the Block Editor Flow

## Goal
Open a generated PRD/BRD and experience clean block rendering with outline navigation, deep links, editing, and diagram visualization.

## Steps
1. Generate PRD‑MP content from sources (existing Think/Define flow).
2. Normalize to blocks:
   - `cat prd.md | sf-blocks normalize --in - --out blocks.json --format json`
3. Open Mission Control → Open PRD/BRD.
4. Verify:
   - Headings, paragraphs, lists, callouts render as blocks.
   - Toggle sections collapse/expand and persist on reload.
   - Outline shows section tree; click navigates and focuses a block.
   - Deep link `#b-<id>` scrolls and highlights the correct block.
   - Diagrams render; editing invalid syntax shows helpful error panel.
5. Edit a block → autosave within ~1.5s → reload to confirm persistence.

## Troubleshooting
- If raw JSON appears: capture logs and file an issue with the input PRD‑MP and blocks.json.
- If diagrams don’t render: inspect inline error with line/column; correct syntax and retry.

