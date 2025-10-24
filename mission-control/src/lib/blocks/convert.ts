import { Block, BlockDocument, BlockType } from './types'
import { generateId } from './uuid'

// Minimal Editor.js -> Blocks conversion (headers, paragraphs, lists, code, mermaid, table, hr)
export function editorJsToBlocks(editorJs: any): Block[] {
  // Special case: Some flows wrap the entire PRD JSON inside a single paragraph block.
  // If we detect that shape, expand the whole document from that JSON and return early.
  try {
    const first = Array.isArray(editorJs?.blocks) ? editorJs.blocks[0] : null
    const txt = first?.data?.text
    if (typeof txt === 'string' && ((/^[({\[]/.test(txt) && txt.length > 40) || /\"Product Specification\"|\"User Stories\"/.test(txt))) {
      const expanded = jsonToBlocks(txt)
      if (expanded.length > 3) {
        return expanded
      }
    }
  } catch {}

  const blocks: Block[] = []
  if (!editorJs || !Array.isArray(editorJs.blocks)) return blocks

  for (const b of editorJs.blocks) {
    const t = (b?.type as string) || ''
    const d = b?.data || {}
    switch (t) {
      case 'header':
        blocks.push({ id: generateId(), type: 'header', content: { level: d.level || 1, text: d.text || '' }, meta: { derivedFrom: 'editorjs' } })
        break
      case 'paragraph':
        // Some legacy PRD flows store the entire JSON payload inside a single paragraph's text.
        // Detect JSON-ish content and expand into proper blocks.
        if (typeof d.text === 'string') {
          const txt = d.text.trim()
          if ((/^[({\[]/.test(txt) && txt.length > 40) || /\"Product Specification\"|\"User Stories\"/.test(txt)) {
            try {
              const expanded = jsonToBlocks(txt)
              if (expanded.length > 1) {
                blocks.push(...expanded)
                break
              }
            } catch (_) {
              // fall through to normal paragraph
            }
          }
        }
        blocks.push({ id: generateId(), type: 'paragraph', content: { text: d.text || '' }, meta: { derivedFrom: 'editorjs' } })
        break
      case 'list':
        blocks.push({ id: generateId(), type: (d.style === 'ordered' ? 'numbered-list' : 'bullet-list') as BlockType, content: { items: d.items || [] }, meta: { derivedFrom: 'editorjs' } })
        break
      case 'code':
        blocks.push({ id: generateId(), type: 'code', content: { code: d.code || '', language: d.language }, meta: { derivedFrom: 'editorjs' } })
        break
      case 'mermaid':
        blocks.push({ id: generateId(), type: 'mermaid-diagram', content: { code: d.code || '' }, meta: { derivedFrom: 'editorjs' } })
        break
      case 'table':
        blocks.push({ id: generateId(), type: 'table', content: { header: d?.content?.[0] ?? undefined, rows: (d?.content || []).slice(1) }, meta: { derivedFrom: 'editorjs' } })
        break
      case 'delimiter':
        blocks.push({ id: generateId(), type: 'hr', content: null, meta: { derivedFrom: 'editorjs' } })
        break
      default:
        // Fallback
        if (d?.text) {
          blocks.push({ id: generateId(), type: 'paragraph', content: { text: String(d.text) }, meta: { derivedFrom: 'editorjs', errors: [`unmapped type ${t}`] } })
        }
    }
  }
  return blocks
}

// Lightweight Markdown -> Blocks (headers, lists, paragraphs, fenced code, mermaid fences, tables)
export function markdownToBlocks(markdown: string): Block[] {
  if (!markdown) return []
  const lines = markdown.split(/\r?\n/)
  const out: Block[] = []
  let i = 0
  let inCode = false
  let fenceLang = ''
  let codeLines: string[] = []
  let listMode: 'bullet' | 'numbered' | null = null
  let listItems: string[] = []

  const flushList = () => {
    if (!listMode || listItems.length === 0) return
    out.push({ id: generateId(), type: listMode === 'numbered' ? 'numbered-list' : 'bullet-list', content: { items: listItems.slice() } })
    listMode = null
    listItems = []
  }

  while (i < lines.length) {
    const raw = lines[i]
    const line = raw.trimEnd()

    // Fences
    const fence = line.match(/^```(.*)$/)
    if (fence) {
      if (!inCode) {
        inCode = true
        fenceLang = (fence[1] || '').trim()
        codeLines = []
      } else {
        // closing fence
        const code = codeLines.join('\n')
        if (fenceLang.startsWith('mermaid')) {
          // Detect diagram type from first non-empty line
          const firstLine = code.split(/\r?\n/).map(s => s.trim()).find(Boolean) || ''
          let diagramType: any = undefined
          if (/^flowchart\b/i.test(firstLine)) diagramType = 'flowchart'
          else if (/^sequenceDiagram\b/i.test(firstLine)) diagramType = 'sequence'
          else if (/^classDiagram\b/i.test(firstLine)) diagramType = 'class'
          else if (/^erDiagram\b/i.test(firstLine)) diagramType = 'er'
          else if (/^stateDiagram\b/i.test(firstLine)) diagramType = 'state'
          else if (/^gantt\b/i.test(firstLine)) diagramType = 'gantt'
          else if (/^pie\b/i.test(firstLine)) diagramType = 'pie'
          else if (/^journey\b/i.test(firstLine)) diagramType = 'user-journey'
          out.push({ id: generateId(), type: 'mermaid-diagram', content: { code, diagramType } as any })
        } else {
          out.push({ id: generateId(), type: 'code', content: { language: fenceLang || undefined, code } })
        }
        inCode = false
        fenceLang = ''
        codeLines = []
      }
      i++
      continue
    }
    if (inCode) {
      codeLines.push(raw)
      i++
      continue
    }

    // Horizontal rule
    if (/^\s*(?:---|\*\*\*|___)\s*$/.test(line)) {
      flushList()
      out.push({ id: generateId(), type: 'hr', content: null })
      i++
      continue
    }

    // Headers
    const h = line.match(/^(#{1,6})\s+(.*)$/)
    if (h) {
      flushList()
      out.push({ id: generateId(), type: 'header', content: { level: h[1].length as 1|2|3|4|5|6, text: h[2].trim() } })
      i++
      continue
    }

    // Numbered list
    if (/^\s*\d+\.\s+/.test(line)) {
      const item = line.replace(/^\s*\d+\.\s+/, '')
      if (listMode !== 'numbered') flushList()
      listMode = 'numbered'
      listItems.push(item)
      i++
      continue
    }

    // Bullet list
    if (/^\s*[-*+]\s+/.test(line)) {
      const item = line.replace(/^\s*[-*+]\s+/, '')
      if (listMode !== 'bullet') flushList()
      listMode = 'bullet'
      listItems.push(item)
      i++
      continue
    }

    // GitHub-flavored Markdown tables (simple detection and parsing)
    const isPotentialTableRow = /\|/.test(line) && !/^\s*<\/?\w/.test(line)
    if (isPotentialTableRow) {
      // Collect contiguous rows with pipe separators
      const tableLines: string[] = []
      let j = i
      while (j < lines.length) {
        const l = lines[j]
        if (l.trim() === '') break
        if (!/\|/.test(l)) break
        // Stop if a new fence starts (safety)
        if (/^```/.test(l.trim())) break
        tableLines.push(l)
        j++
      }

      if (tableLines.length >= 2) {
        // Check for alignment row on second line
        const parts = (s: string) => s.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim())
        const row1 = parts(tableLines[0])
        const row2 = parts(tableLines[1])
        const alignRow = row2.every(c => /^:?-{3,}:?$/.test(c))
        let header: string[] | undefined = undefined
        const rows: string[][] = []
        if (alignRow) {
          header = row1
          for (let k = 2; k < tableLines.length; k++) rows.push(parts(tableLines[k]))
        } else {
          // No alignment row; treat all as body
          rows.push(row1)
          for (let k = 1; k < tableLines.length; k++) rows.push(parts(tableLines[k]))
        }
        if (rows.length > 0 || header) {
          flushList()
          out.push({ id: generateId(), type: 'table', content: { header, rows } as any })
          i = j
          continue
        }
      }
    }

    // Paragraph aggregation (until blank or special)
    if (line.trim().length > 0) {
      flushList()
      const para: string[] = [line.trim()]
      let j = i + 1
      while (j < lines.length) {
        const next = lines[j]
        if (
          next.trim() === '' ||
          /^\s*(?:---|\*\*\*|___)\s*$/.test(next) ||
          /^(#{1,6})\s+/.test(next) ||
          /^\s*\d+\.\s+/.test(next) ||
          /^\s*[-*+]\s+/.test(next) ||
          /^```/.test(next) ||
          /\|/.test(next)
        ) {
          break
        }
        para.push(next.trim())
        j++
      }
      out.push({ id: generateId(), type: 'paragraph', content: { text: para.join(' ') } })
      i = j
      continue
    }

    // Blank line
    flushList()
    i++
  }

  flushList()
  return out
}

export function toDocument(blocks: Block[], title?: string): BlockDocument {
  return { meta: { title }, blocks }
}

// Blocks -> Markdown (for export). Covers common block types used in MVP.
export function blocksToMarkdown(blocks: Block[]): string {
  const lines: string[] = []
  for (const b of blocks) {
    switch (b.type) {
      case 'header': {
        const lvl = Math.min(Math.max(((b as any).content?.level ?? 1) as number, 1), 6)
        const txt = (b as any).content?.text ?? ''
        lines.push(`${'#'.repeat(lvl)} ${txt}`)
        lines.push('')
        break
      }
      case 'paragraph': {
        const txt = (b as any).content?.text ?? ''
        lines.push(txt)
        lines.push('')
        break
      }
      case 'bullet-list': {
        const items: string[] = (b as any).content?.items || []
        for (const it of items) lines.push(`- ${it}`)
        lines.push('')
        break
      }
      case 'numbered-list': {
        const items: string[] = (b as any).content?.items || []
        items.forEach((it, idx) => lines.push(`${idx + 1}. ${it}`))
        lines.push('')
        break
      }
      case 'code': {
        const lang = (b as any).content?.language || ''
        const code = (b as any).content?.code || ''
        lines.push('```' + lang)
        lines.push(code)
        lines.push('```')
        lines.push('')
        break
      }
      case 'mermaid-diagram': {
        const code = (b as any).content?.code || ''
        lines.push('```mermaid')
        lines.push(code)
        lines.push('```')
        lines.push('')
        break
      }
      case 'table': {
        const header: string[] | undefined = (b as any).content?.header
        const rows: string[][] = (b as any).content?.rows || []
        const renderRow = (r: string[]) => `| ${r.join(' | ')} |`
        if (header && header.length) {
          lines.push(renderRow(header))
          lines.push(renderRow(header.map(() => '---')))
        }
        for (const r of rows) lines.push(renderRow(r))
        lines.push('')
        break
      }
      case 'hr':
        lines.push('---')
        lines.push('')
        break
      default:
        break
    }
  }
  // Trim trailing blank line
  while (lines.length && lines[lines.length - 1] === '') lines.pop()
  return lines.join('\n')
}

// Fallback: Convert JSON (object/array) to readable blocks.
// This is intentionally lightweight and opinionated to avoid bloat.
function titleCase(s: string): string {
  return s
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\w\S*/g, (w) => w.charAt(0).toUpperCase() + w.slice(1))
}

function summarizeObjectRow(o: Record<string, any>): string {
  const entries = Object.entries(o)
    .filter(([_, v]) => typeof v !== 'object')
    .slice(0, 4)
    .map(([k, v]) => `${k}: ${String(v)}`)
  return entries.join(' · ') || JSON.stringify(o)
}

function tryParseLoosely(raw: string): any {
  // Normalize smart quotes first
  const normalizedQuotes = raw
    .replace(/[\u201C\u201D\u201E\u201F\u2033]/g, '"') // fancy double quotes → straight
    .replace(/[\u2018\u2019\u201A\u201B\u2032]/g, "'") // fancy single quotes → straight

  // 1) direct parse
  try { return JSON.parse(normalizedQuotes) } catch {}
  // 2) strip surrounding parentheses or whitespace
  const trimmed = normalizedQuotes.trim()
  const noParens = trimmed.startsWith('(') && trimmed.endsWith(')')
    ? trimmed.slice(1, -1).trim()
    : trimmed
  try { return JSON.parse(noParens) } catch {}
  // 3) extract first balanced JSON-looking chunk with simple depth scan
  const startIdx = (() => {
    const i1 = noParens.indexOf('{')
    const i2 = noParens.indexOf('[')
    if (i1 === -1) return i2
    if (i2 === -1) return i1
    return Math.min(i1, i2)
  })()
  if (startIdx !== -1) {
    const open = noParens[startIdx]
    const close = open === '{' ? '}' : ']'
    let depth = 0
    let inStr: 'single' | 'double' | null = null
    let escaped = false
    for (let j = startIdx; j < noParens.length; j++) {
      const ch = noParens[j]
      if (inStr) {
        if (!escaped && ((inStr === 'double' && ch === '"') || (inStr === 'single' && ch === "'"))) inStr = null
        escaped = ch === '\\' && !escaped
        continue
      }
      if (ch === '"') { inStr = 'double'; continue }
      if (ch === "'") { inStr = 'single'; continue }
      if (ch === open) depth++
      else if (ch === close) {
        depth--
        if (depth === 0) {
          const slice = noParens.slice(startIdx, j + 1)
          try { return JSON.parse(slice) } catch {}
          break
        }
      }
    }
  }
  // 4) replace single quotes with double (very loose)
  const relaxed = noParens
    .replace(/\bNone\b/g, 'null')
    .replace(/\bTrue\b/g, 'true')
    .replace(/\bFalse\b/g, 'false')
    .replace(/'([^']*)'/g, (m, g1) => '"' + g1.replace(/"/g, '\\"') + '"')
  try { return JSON.parse(relaxed) } catch {}
  throw new Error('Unable to parse JSON-ish string')
}

export function jsonToBlocks(input: unknown): Block[] {
  let data: any = input
  if (typeof input === 'string') {
    try {
      data = tryParseLoosely(input)
    } catch {
      // Not valid JSON-ish – return as a paragraph
      return [
        { id: generateId(), type: 'paragraph', content: { text: String(input) } },
      ]
    }
  }

  const out: Block[] = []

  const walk = (value: any, level: number, key?: string) => {
    const headerLevel = Math.min(Math.max(level, 1), 6) as 1 | 2 | 3 | 4 | 5 | 6
    if (key) {
      out.push({ id: generateId(), type: 'header', content: { level: headerLevel, text: titleCase(key) } })
    }

    if (Array.isArray(value)) {
      if (value.length === 0) {
        out.push({ id: generateId(), type: 'paragraph', content: { text: '—' } })
        return
      }
      // Primitive array → bullet list
      if (value.every(v => typeof v !== 'object')) {
        out.push({ id: generateId(), type: 'bullet-list', content: { items: value.map(v => String(v)) } })
        return
      }
      // Array of objects → bullet list with compact summaries
      out.push({ id: generateId(), type: 'bullet-list', content: { items: value.map(v => summarizeObjectRow(v || {})) } })
      return
    }

    if (value && typeof value === 'object') {
      const entries = Object.entries(value)
      if (entries.length === 0) {
        out.push({ id: generateId(), type: 'paragraph', content: { text: '{}' } })
        return
      }
      for (const [k, v] of entries) {
        // One level deeper for each key
        walk(v, headerLevel + 1, k)
      }
      return
    }

    // Primitive
    if (value === null || value === undefined) {
      out.push({ id: generateId(), type: 'paragraph', content: { text: '—' } })
    } else {
      out.push({ id: generateId(), type: 'paragraph', content: { text: String(value) } })
    }
  }

  // Root handling
  if (Array.isArray(data)) {
    walk(data, 1, 'Items')
  } else if (data && typeof data === 'object') {
    // Emit H1 per top-level key to avoid an extra blank wrapper
    for (const [k, v] of Object.entries(data)) {
      walk(v, 1, k)
    }
  } else {
    out.push({ id: generateId(), type: 'paragraph', content: { text: String(data) } })
  }

  return out
}

// Heuristic parser for "JSON-ish" PRD strings produced by some LLMs (missing commas, embedded mermaid, etc.).
// Not a full JSON parser: matches known section labels and extracts arrays/objects of arrays into blocks.
export function jsonishPrdToBlocks(raw: string): Block[] {
  const s = (raw || '').replace(/\r/g, '')
  const out: Block[] = []

  const addHeader = (level: 1|2|3|4|5|6, text: string) => out.push({ id: generateId(), type: 'header', content: { level, text } })
  const addPara = (text: string) => { if (text && text.trim()) out.push({ id: generateId(), type: 'paragraph', content: { text: text.trim() } }) }
  const addList = (items: string[], ordered = false) => {
    if (items && items.length) out.push({ id: generateId(), type: ordered ? 'numbered-list' : 'bullet-list', content: { items } as any })
  }
  const addMermaid = (code: string) => { if (code && code.trim()) out.push({ id: generateId(), type: 'mermaid-diagram', content: { code } as any }) }

  const topKeys = [
    'Product Specification',
    'Technical Specification',
    'Implementation Plan',
  ]

  const findSection = (label: string): { start: number, end: number, body: string } | null => {
    const marker = `"${label}"` // expecting e.g. "Product Specification"
    const idx = s.indexOf(marker)
    if (idx === -1) return null
    // Find next top-level label
    let next = s.length
    for (const k of topKeys) {
      if (k === label) continue
      const j = s.indexOf(`"${k}"`, idx + marker.length)
      if (j !== -1 && j < next) next = j
    }
    const body = s.slice(idx + marker.length, next)
    return { start: idx, end: next, body }
  }

  // Global title
  addHeader(1, 'Product Requirements Document')

  // Mermaid triple-quote blocks (very loose)
  const mermaidBlocks = [...s.matchAll(/"""\s*mermaid([\s\S]*?)"""/g)]
  for (const m of mermaidBlocks) addMermaid((m[1] || '').trim())

  // Helper to extract arrays of strings within a text chunk
  const pickArrayItems = (chunk: string): string[] => {
    // Grab quoted strings that look like list entries
    const items: string[] = []
    const re = /"([^"\n]{3,})"/g
    let mm: RegExpExecArray | null
    while ((mm = re.exec(chunk))) {
      const val = mm[1].trim()
      if (!/^[A-Za-z][A-Za-z\s\-:()\[\],.%/]+$/.test(val)) continue
      // Skip keys (followed by ":")
      const after = chunk.slice(mm.index + mm[0].length).trimStart()
      if (after.startsWith(':')) continue
      items.push(val)
    }
    // De-dup and trim
    return Array.from(new Set(items))
  }

  const parseProductSpec = (body: string) => {
    addHeader(2, 'Product Specification')
    // Introduction & Vision (string)
    const intro = body.match(/"Introduction\s*&\s*Vision"\s*:\s*"([\s\S]*?)"\s*(?:\n|\r|\s)/)
    if (intro) addPara(intro[1])
    // User Stories (array)
    const stories = body.match(/"User Stories\s*\/\s*Use Cases"\s*:\s*\[([\s\S]*?)\]/)
    if (stories) addList(pickArrayItems(stories[1]))
    // Functional Requirements (object of arrays)
    const fr = body.match(/"Functional Requirements"\s*:\s*\{([\s\S]*?)\}/)
    if (fr) {
      const catRe = /"([^"]+)"\s*:\s*\[([\s\S]*?)\]/g
      let m: RegExpExecArray | null
      while ((m = catRe.exec(fr[1]))) {
        addHeader(3, m[1])
        addList(pickArrayItems(m[2]))
      }
    }
    // Non-Functional Requirements (object of simple strings or arrays)
    const nfr = body.match(/"Non-Functional Requirements"\s*:\s*\{([\s\S]*?)\}/)
    if (nfr) {
      const kvRe = /"([^"]+)"\s*:\s*"([^"]*)"/g
      let m: RegExpExecArray | null
      const pairs: string[] = []
      while ((m = kvRe.exec(nfr[1]))) pairs.push(`${m[1]}: ${m[2]}`)
      if (pairs.length) addList(pairs)
    }
    // Success Metrics (object key: value)
    const sm = body.match(/"Success Metrics"\s*:\s*\{([\s\S]*?)\}/)
    if (sm) {
      const kvRe = /"([^"]+)"\s*:\s*"([^"]*)"/g
      let m: RegExpExecArray | null
      const pairs: string[] = []
      while ((m = kvRe.exec(sm[1]))) pairs.push(`${m[1]}: ${m[2]}`)
      if (pairs.length) addList(pairs)
    }
  }

  const parseTechnicalSpec = (body: string) => {
    addHeader(2, 'Technical Specification')
    const overview = body.match(/"System Overview"\s*:\s*"([\s\S]*?)"\s*(?:\n|\r|\s)/)
    if (overview) addPara(overview[1])
  }

  const parseImplementationPlan = (body: string) => {
    addHeader(2, 'Implementation Plan')
    const phaseRe = /"Phase\s*(\d+)"\s*:\s*\{([\s\S]*?)\}/g
    let m: RegExpExecArray | null
    while ((m = phaseRe.exec(body))) {
      const name = (m[2].match(/"name"\s*:\s*"([^"]+)"/) || [])[1]
      const tasks = (m[2].match(/"tasks"\s*:\s*\[([\s\S]*?)\]/) || [])[1]
      if (name) addHeader(3, `${m[1]}. ${name}`)
      if (tasks) addList(pickArrayItems(tasks))
    }
  }

  const ps = findSection('Product Specification'); if (ps) parseProductSpec(ps.body)
  const ts = findSection('Technical Specification'); if (ts) parseTechnicalSpec(ts.body)
  const ip = findSection('Implementation Plan'); if (ip) parseImplementationPlan(ip.body)

  // If heuristics produced only the title, fall back to a single paragraph to avoid empty page
  if (out.length <= 1) {
    return [{ id: generateId(), type: 'paragraph', content: { text: raw } }]
  }
  return out
}
