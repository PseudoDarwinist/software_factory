# Contract – CLI `sf-blocks normalize`

## Purpose
Normalize PRD‑MP Markdown into a canonical Block Document JSON to feed the editor and APIs.

## Invocation
`sf-blocks normalize --in <path|-> --out <path|-> --format json|text --strict --version`

## Inputs
- stdin or file path containing PRD‑MP Markdown
- Flags:
  - `--in`: input path or `-` for stdin
  - `--out`: output path or `-` for stdout
  - `--format`: `json` (default) or `text` (for debug pretty print)
  - `--strict`: fail on unknown fences/tokens
  - `--version`: print version and exit

## Outputs
- Exit code 0 on success
- Stdout (or file): Block Document JSON matching schema (see `blocks.schema.json`)
- Stderr: structured errors/warnings (JSON lines) with `trace_id`, `line`, `column`, `message`

## Examples
```
cat doc.md | sf-blocks normalize --in - --out - --format json > blocks.json
sf-blocks normalize --in spec.md --out blocks.json --strict
```

## Error Cases
- Invalid diagram fence → non‑zero exit, error object with line/column
- Unknown callout syntax (strict) → non‑zero exit; (non‑strict) → warning, fallback to paragraph

