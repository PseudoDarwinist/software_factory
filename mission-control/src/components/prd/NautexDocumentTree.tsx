import React, { useState } from 'react'
import { Block, HeaderContent } from '@/lib/blocks/types'

interface DocumentTreeProps {
  blocks: Block[]
  title?: string
}

interface TreeItem {
  id: string
  text: string
  level: number
  isExpanded: boolean
  children: TreeItem[]
}

const ChevronDownIcon = () => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
    <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

const ChevronRightIcon = () => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
    <path d="M4.5 3L7.5 6L4.5 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

const DocumentIcon = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <path d="M3 2V12C3 12.2652 3.10536 12.5196 3.29289 12.7071C3.48043 12.8946 3.73478 13 4 13H10C10.2652 13 10.5196 12.8946 10.7071 12.7071C10.8946 12.5196 11 12.2652 11 12V4.5L8.5 2H3Z" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M8.5 2V4.5H11" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

export const NautexDocumentTree: React.FC<DocumentTreeProps> = ({ 
  blocks, 
  title = "Product Specification" 
}) => {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set())
  const [activeSection, setActiveSection] = useState<string>('')

  // Build hierarchical tree structure from blocks
  const buildTree = (blocks: Block[]): TreeItem[] => {
    const tree: TreeItem[] = []
    
    for (const block of blocks) {
      if (block.type === 'header') {
        const content = block.content as HeaderContent
        tree.push({
          id: block.id || Math.random().toString(),
          text: content.text,
          level: content.level,
          isExpanded: expandedSections.has(block.id || ''),
          children: []
        })
      }
    }
    
    return tree
  }

  const toggleExpanded = (id: string) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedSections(newExpanded)
  }

  const scrollToSection = (id: string) => {
    setActiveSection(id)
    const element = document.querySelector(`[data-block-id="${id}"]`)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  const tree = buildTree(blocks)

  const renderTreeItem = (item: TreeItem, depth: number = 0) => {
    const isActive = activeSection === item.id
    const hasChildren = item.children.length > 0
    
    return (
      <div key={item.id}>
        <div
          className="nautex-tree-item"
          onClick={() => scrollToSection(item.id)}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '6px 8px',
            marginLeft: `${depth * 16}px`,
            cursor: 'pointer',
            borderRadius: '4px',
            fontSize: '13px',
            fontWeight: isActive ? '600' : '500',
            color: isActive ? '#16a34a' : '#4b5563',
            background: isActive ? 'rgba(34, 197, 94, 0.1)' : 'transparent',
            transition: 'all 0.15s ease'
          }}
          onMouseEnter={(e) => {
            if (!isActive) {
              e.currentTarget.style.background = 'rgba(34, 197, 94, 0.05)'
              e.currentTarget.style.color = '#16a34a'
            }
          }}
          onMouseLeave={(e) => {
            if (!isActive) {
              e.currentTarget.style.background = 'transparent'
              e.currentTarget.style.color = '#4b5563'
            }
          }}
        >
          {hasChildren && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                toggleExpanded(item.id)
              }}
              style={{
                background: 'none',
                border: 'none',
                padding: '0',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                color: '#6b7280'
              }}
            >
              {item.isExpanded ? <ChevronDownIcon /> : <ChevronRightIcon />}
            </button>
          )}
          
          {!hasChildren && (
            <div style={{ width: '12px', height: '12px' }} />
          )}
          
          <span style={{ 
            flex: 1,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap'
          }}>
            {item.text}
          </span>
        </div>
        
        {/* Render children if expanded */}
        {hasChildren && item.isExpanded && (
          <div>
            {item.children.map(child => renderTreeItem(child, depth + 1))}
          </div>
        )}
      </div>
    )
  }

  return (
    <div style={{ padding: '8px 0' }}>
      {/* Document title */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        padding: '8px',
        marginBottom: '8px',
        color: '#1f2937',
        fontWeight: '600',
        fontSize: '14px'
      }}>
        <DocumentIcon />
        <span>{title}</span>
      </div>

      {/* Tree items */}
      <div>
        {tree.length === 0 ? (
          <div style={{ 
            padding: '16px 8px', 
            color: '#6b7280', 
            fontSize: '12px',
            fontStyle: 'italic',
            textAlign: 'center'
          }}>
            No sections yet
          </div>
        ) : (
          tree.map(item => renderTreeItem(item))
        )}
      </div>
    </div>
  )
}