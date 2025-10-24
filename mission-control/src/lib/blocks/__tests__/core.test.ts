import { generateId } from '../uuid'
import { validateBlock, validateDocument } from '../validate'
import { editorJsToBlocks, markdownToBlocks, blocksToMarkdown } from '../convert'

describe('blocks core', () => {
  test('generateId returns unique ids', () => {
    const a = generateId()
    const b = generateId()
    expect(a).not.toEqual(b)
    expect(a).toContain('b_')
  })

  test('validate paragraph block', () => {
    const block = { id: generateId(), type: 'paragraph' as const, content: { text: 'Hello' } }
    const res = validateBlock(block)
    expect(res.ok).toBe(true)
  })

  test('markdown to blocks - headers and lists', () => {
    const md = [
      '# Title',
      '',
      'Paragraph text.',
      '',
      '- a',
      '- b',
      '',
      '1. one',
      '2. two',
      '',
      '---',
      '',
      '```mermaid',
      'flowchart LR; A-->B',
      '```',
    ].join('\n')
    const blocks = markdownToBlocks(md)
    expect(blocks.find(b => b.type === 'header')).toBeTruthy()
    expect(blocks.find(b => b.type === 'paragraph')).toBeTruthy()
    expect(blocks.find(b => b.type === 'bullet-list')).toBeTruthy()
    expect(blocks.find(b => b.type === 'numbered-list')).toBeTruthy()
    expect(blocks.find(b => b.type === 'hr')).toBeTruthy()
    expect(blocks.find(b => b.type === 'mermaid-diagram')).toBeTruthy()
    expect(validateDocument(blocks).ok).toBe(true)
  })

  test('markdown tables and code fences', () => {
    const md = [
      '| Name | Age |',
      '| ---- | --- |',
      '| Alice | 30 |',
      '| Bob | 25 |',
      '',
      '```python',
      "print('hi')",
      '```',
      '',
    ].join('\n')

    const blocks = markdownToBlocks(md)
    const tbl = blocks.find(b => b.type === 'table') as any
    expect(tbl).toBeTruthy()
    expect(tbl.content.header).toEqual(['Name', 'Age'])
    expect(tbl.content.rows.length).toBe(2)
    const code = blocks.find(b => b.type === 'code') as any
    expect(code.content.language).toBe('python')
  })

  test('blocks to markdown export', () => {
    const blocks = markdownToBlocks(`# Title\n\n- a\n- b\n\nParagraph.`)
    const md = blocksToMarkdown(blocks)
    expect(md).toContain('# Title')
    expect(md).toContain('- a')
    expect(md).toContain('Paragraph.')
  })

  test('editorjs to blocks - basic types', () => {
    const ej = {
      blocks: [
        { type: 'header', data: { level: 2, text: 'H2' } },
        { type: 'paragraph', data: { text: 'P' } },
        { type: 'list', data: { style: 'unordered', items: ['x', 'y'] } },
        { type: 'delimiter', data: {} },
      ],
    }
    const blocks = editorJsToBlocks(ej)
    expect(blocks.map(b => b.type)).toEqual([
      'header',
      'paragraph',
      'bullet-list',
      'hr',
    ])
  })
})
