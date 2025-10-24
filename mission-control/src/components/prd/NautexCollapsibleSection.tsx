import React, { useState } from 'react'
import { Block, HeaderContent } from '@/lib/blocks/types'
import { DiagramBlock } from './blocks/DiagramBlock'

interface NautexCollapsibleSectionProps {
  headerBlock: Block
  children: Block[]
  onUpdate?: (blockId: string, content: any) => void
  isEditable?: boolean
}

const ChevronDownIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M4 6L8 10L12 6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

const ChevronRightIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M6 4L10 8L6 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

export const NautexCollapsibleSection: React.FC<NautexCollapsibleSectionProps> = ({
  headerBlock,
  children,
  onUpdate,
  isEditable = true
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const headerContent = headerBlock.content as HeaderContent
  const level = headerContent.level
  
  // Style based on header level (H1, H2, H3, etc.)
  const getHeaderStyle = () => {
    switch (level) {
      case 1:
        return {
          fontSize: '24px',
          fontWeight: '700',
          color: '#1f2937',
          marginBottom: '16px'
        }
      case 2:
        return {
          fontSize: '20px',
          fontWeight: '600', 
          color: '#1f2937',
          marginBottom: '12px'
        }
      case 3:
        return {
          fontSize: '18px',
          fontWeight: '600',
          color: '#1f2937',
          marginBottom: '10px'
        }
      default:
        return {
          fontSize: '16px',
          fontWeight: '600',
          color: '#1f2937',
          marginBottom: '8px'
        }
    }
  }

  const renderChildBlock = (block: Block) => {
    switch (block.type) {
      case 'paragraph':
        return (
          <div 
            key={block.id}
            className="nautex-content"
          >
            {(block.content as any)?.text || ''}
          </div>
        )
      case 'bullet-list':
      case 'numbered-list':
        return (
          <ul 
            key={block.id} 
            className="nautex-list"
          >
            {(block.content as any)?.items?.map((item: string, i: number) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        )
      case 'code':
        return (
          <pre 
            key={block.id}
            className="nautex-code"
          >
            <code>{(block.content as any)?.code}</code>
          </pre>
        )
      case 'mermaid-diagram':
        return (
          <div key={block.id} className="nautex-diagram">
            <DiagramBlock 
              block={block} 
              onUpdate={(updatedBlock) => {
                if (onUpdate) {
                  onUpdate(block.id || '', updatedBlock.content)
                }
              }} 
            />
          </div>
        )
      case 'table':
        return (
          <div key={block.id} style={{ 
            margin: '16px 0',
            overflowX: 'auto'
          }}>
            <table style={{
              width: '100%',
              borderCollapse: 'collapse',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
              fontSize: '14px'
            }}>
              {/* Basic table rendering - you can enhance this */}
              <tbody>
                <tr>
                  <td style={{ 
                    padding: '8px 12px',
                    border: '1px solid #e5e7eb',
                    color: '#6b7280'
                  }}>
                    Table content: {JSON.stringify((block.content as any) || {})}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        )
      default:
        return (
          <div key={block.id} style={{ color: '#6b7280', fontSize: '14px', marginBottom: '8px' }}>
            {JSON.stringify(block.content)}
          </div>
        )
    }
  }

  return (
    <div className="nautex-section">
      {/* Collapsible Header */}
      <div
        className={`nautex-collapse-button nautex-header-${level}`}
        onClick={() => setIsCollapsed(!isCollapsed)}
        style={getHeaderStyle()}
      >
        {/* Chevron Icon */}
        <div style={{ 
          color: '#6b7280',
          display: 'flex',
          alignItems: 'center',
          minWidth: '16px'
        }}>
          {isCollapsed ? <ChevronRightIcon /> : <ChevronDownIcon />}
        </div>
        
        {/* Header Text */}
        <span>{headerContent.text}</span>
      </div>

      {/* Collapsible Content */}
      {!isCollapsed && (
        <div className="nautex-section-content">
          {children.map(renderChildBlock)}
        </div>
      )}
    </div>
  )
}

// Document structure parser to group content under headers
export const parseDocumentStructure = (blocks: Block[]) => {
  const sections: Array<{
    header: Block
    children: Block[]
  }> = []
  
  let currentSection: { header: Block; children: Block[] } | null = null
  
  for (const block of blocks) {
    if (block.type === 'header') {
      // Save previous section if exists
      if (currentSection) {
        sections.push(currentSection)
      }
      
      // Start new section
      currentSection = {
        header: block,
        children: []
      }
    } else if (currentSection) {
      // Add block to current section
      currentSection.children.push(block)
    } else {
      // Create default section for blocks without headers
      if (!currentSection) {
        currentSection = {
          header: {
            id: 'default-header',
            type: 'header',
            content: { text: 'Document Content', level: 1 }
          } as Block,
          children: []
        }
      }
      currentSection.children.push(block)
    }
  }
  
  // Don't forget the last section
  if (currentSection) {
    sections.push(currentSection)
  }
  
  return sections
}