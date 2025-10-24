import React, { useState } from 'react'
import { Block } from '@/lib/blocks/types'
import { HeaderBlock } from './blocks/HeaderBlock'
import { ParagraphBlock } from './blocks/ParagraphBlock'
import { DiagramBlock } from './blocks/DiagramBlock'
import { TableBlock } from './blocks/TableBlock'
import { BlockControls } from './BlockControls'
import { NautexCollapsibleSection, parseDocumentStructure } from './NautexCollapsibleSection'
import { missionControlApi } from '@/services/api/missionControlApi'

export const BlockRenderer: React.FC<{ 
  blocks: Block[];
  sessionId?: string;
  onBlocksChange?: (blocks: Block[]) => void;
}> = ({ blocks, sessionId, onBlocksChange }) => {
  const [localBlocks, setLocalBlocks] = useState(blocks)

  // Update local blocks when props change
  React.useEffect(() => {
    setLocalBlocks(blocks)
  }, [blocks])

  const updateBlock = async (blockId: string, content: any) => {
    try {
      // Update locally first for optimistic updates
      const updatedBlocks = localBlocks.map(block => 
        block.id === blockId ? { ...block, content } : block
      )
      setLocalBlocks(updatedBlocks)
      
      // Call parent callback
      if (onBlocksChange) {
        onBlocksChange(updatedBlocks)
      }

      // Persist to backend if sessionId is provided
      if (sessionId) {
        await missionControlApi.updateBlock(blockId, content, sessionId)
      }
    } catch (error) {
      console.error('Failed to update block:', error)
      // Revert optimistic update on error
      setLocalBlocks(blocks)
    }
  }

  const deleteBlock = async (blockId: string) => {
    try {
      // Update locally first
      const updatedBlocks = localBlocks.filter(block => block.id !== blockId)
      setLocalBlocks(updatedBlocks)
      
      // Call parent callback
      if (onBlocksChange) {
        onBlocksChange(updatedBlocks)
      }

      // Persist to backend if sessionId is provided
      if (sessionId) {
        await missionControlApi.deleteBlock(blockId, sessionId)
      }
    } catch (error) {
      console.error('Failed to delete block:', error)
      // Revert optimistic update on error
      setLocalBlocks(blocks)
    }
  }

  const renderBlock = (b: Block) => {
    const commonProps = {
      key: b.id,
      blockId: b.id,
      onUpdate: (content: any) => updateBlock(b.id, content),
      isEditable: true
    }

    switch (b.type) {
      case 'header':
        return <HeaderBlock {...commonProps} content={b.content as any} />
      case 'paragraph':
        return <ParagraphBlock {...commonProps} content={b.content as any} />
      case 'bullet-list':
      case 'numbered-list':
        return (
          <ul key={b.id} data-block-id={b.id} style={{ margin: '0.5rem 1.25rem' }}>
            {(b.content as any)?.items?.map((it: string, i: number) => (
              <li key={i}>{it}</li>
            ))}
          </ul>
        )
      case 'hr':
        return <hr key={b.id} data-block-id={b.id} style={{ opacity: 0.2, margin: '1rem 0' }} />
      case 'code':
        return (
          <pre key={b.id} data-block-id={b.id} style={{ background: '#f8fafc', padding: '0.75rem', borderRadius: 8, overflowX: 'auto', color: '#1f2937', border: '1px solid #e5e7eb' }}>
            <code>{(b.content as any)?.code}</code>
          </pre>
        )
      case 'mermaid-diagram':
        return <DiagramBlock key={b.id} block={b} onUpdate={(updatedBlock) => updateBlock(b.id, updatedBlock.content)} />
      case 'table':
        return <TableBlock key={b.id} block={b} />
      default:
        return null
    }
  }

  // Parse blocks into collapsible sections like Nautex
  const sections = parseDocumentStructure(localBlocks)

  return (
    <div style={{ position: 'relative' }}>
      {localBlocks.length === 0 && (
        <div style={{ 
          padding: '2rem', 
          textAlign: 'center', 
          color: '#6b7280',
          fontStyle: 'italic' 
        }}>
          No content available
        </div>
      )}
      
      {/* Render as Nautex-style collapsible sections */}
      {sections.map((section, index) => (
        <NautexCollapsibleSection
          key={section.header.id || index}
          headerBlock={section.header}
          children={section.children}
          onUpdate={updateBlock}
          isEditable={true}
        />
      ))}
    </div>
  )
}
