# Contract – Blocks REST API

## GET /api/docs/{id}/blocks
- Purpose: Retrieve normalized Block Document for a document id.
- Response 200: `{ id, title, version, blocks: Block[], outline: OutlineIndex[] }`
- Response 404: `{ error: "not_found", id }`
- Headers: `X-Trace-Id`

## PUT /api/docs/{id}/blocks
- Purpose: Replace current Block Document with a new version after edits.
- Request: `{ blocks: Block[], outline, meta }`
- Response 200: `{ status: "ok", version, saved_at }`
- Response 409: `{ error: "version_conflict", expected, actual }`
- Validation: schema must match `blocks.schema.json`.

## GET /api/docs/{id}
- Purpose: Retrieve original PRD‑MP and metadata.
- Response 200: `{ id, original_interchange, meta }`

## Error Envelope (common)
`{ error: { code, message, details? }, trace_id }`

