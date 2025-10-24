import React from 'react'
import type { Block } from '@/lib/blocks/types'

export const TableBlock: React.FC<{ block: Block }> = ({ block }) => {
  const content: any = (block as any).content || {}
  const header: string[] | undefined = content.header
  const rows: string[][] = content.rows || []
  return (
    <div data-block-id={block.id} style={{ overflowX: 'auto', margin: '0.5rem 0' }}>
      <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 400 }}>
        {header && (
          <thead>
            <tr>
              {header.map((h: string, i: number) => (
                <th key={i} style={{ textAlign: 'left', borderBottom: '1px solid rgba(255,255,255,0.08)', padding: '6px 8px' }}>{h}</th>
              ))}
            </tr>
          </thead>
        )}
        <tbody>
          {rows.map((r: string[], i: number) => (
            <tr key={i}>
              {r.map((c: string, j: number) => (
                <td key={j} style={{ borderBottom: '1px solid rgba(255,255,255,0.06)', padding: '6px 8px', whiteSpace: 'pre-wrap' }}>{c}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

