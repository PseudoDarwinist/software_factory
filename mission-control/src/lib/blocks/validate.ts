import { Block, BlockType } from './types'

export type ValidationResult = { ok: true } | { ok: false; errors: string[] }

export function validateBlock(block: Block): ValidationResult {
  const errors: string[] = []

  if (!block) return { ok: false, errors: ['Block is undefined'] }

  if (!block.id) errors.push('Missing id')
  if (!block.type) errors.push('Missing type')

  const t: BlockType = block.type
  const c: any = block.content

  switch (t) {
    case 'paragraph':
      if (!c || typeof c.text !== 'string') errors.push('paragraph.content.text must be string')
      break
    case 'header':
      if (!c || typeof c.text !== 'string') errors.push('header.content.text must be string')
      if (!c || ![1, 2, 3, 4, 5, 6].includes(c.level)) errors.push('header.content.level must be 1..6')
      break
    case 'bullet-list':
    case 'numbered-list':
      if (!c || !Array.isArray(c.items)) errors.push('list.content.items must be array')
      break
    case 'code':
      if (!c || typeof c.code !== 'string') errors.push('code.content.code must be string')
      break
    case 'mermaid-diagram':
      if (!c || typeof c.code !== 'string') errors.push('mermaid.content.code must be string')
      break
    case 'table':
      if (!c || !Array.isArray(c.rows)) errors.push('table.content.rows must be array')
      break
    case 'hr':
      // no content requirements
      break
    default:
      errors.push(`Unknown block type: ${t as string}`)
  }

  return errors.length ? { ok: false, errors } : { ok: true }
}

export function validateDocument(blocks: Block[]): ValidationResult {
  const errors: string[] = []
  if (!Array.isArray(blocks)) return { ok: false, errors: ['Document must be an array'] }
  blocks.forEach((b, i) => {
    const res = validateBlock(b)
    if (!res.ok) errors.push(`Block[${i}]: ${res.errors.join('; ')}`)
  })
  return errors.length ? { ok: false, errors } : { ok: true }
}

