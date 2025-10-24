import React, { useState, useEffect, useCallback } from 'react'
import { Block, HeaderContent } from '@/lib/blocks/types'
import './notion-styles.css'

interface TOCItem {
  id: string
  text: string
  level: number
  element?: HTMLElement
}

interface SidebarTOCProps {
  blocks: Block[]
  className?: string
}

export const SidebarTOC: React.FC<SidebarTOCProps> = ({ blocks, className = '' }) => {
  const [tocItems, setTocItems] = useState<TOCItem[]>([])
  const [activeId, setActiveId] = useState<string>('')

  // Extract headers from blocks
  useEffect(() => {
    const headers: TOCItem[] = blocks
      .filter(block => block.type === 'header')
      .map(block => ({
        id: block.id || '',
        text: (block.content as HeaderContent).text,
        level: (block.content as HeaderContent).level
      }))
    
    setTocItems(headers)
  }, [blocks])

  // Set up intersection observer for scroll sync
  useEffect(() => {
    if (tocItems.length === 0) return

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const id = entry.target.getAttribute('data-block-id')
            if (id) {
              setActiveId(id)
            }
          }
        })
      },
      {
        rootMargin: '-20% 0% -35% 0%',
        threshold: 0
      }
    )

    // Observe all header elements
    const headerElements = document.querySelectorAll('[data-block-id]')
    headerElements.forEach(el => {
      const blockId = el.getAttribute('data-block-id')
      const isHeader = tocItems.some(item => item.id === blockId)
      if (isHeader) {
        observer.observe(el)
      }
    })

    return () => observer.disconnect()
  }, [tocItems])

  // Handle click to scroll to section
  const handleItemClick = useCallback((id: string) => {
    const element = document.querySelector(`[data-block-id="${id}"]`)
    if (element) {
      element.scrollIntoView({ 
        behavior: 'smooth', 
        block: 'start',
        inline: 'nearest' 
      })
      setActiveId(id)
    }
  }, [])

  if (tocItems.length === 0) {
    return (
      <div className={className}>
        <div style={{ padding: '1rem', color: '#6b7280' }}>
          <div style={{ fontSize: '14px', marginBottom: '0.5rem' }}>No sections yet</div>
          <div style={{ fontSize: '12px', opacity: 0.7 }}>
            Add headers to create navigation
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className={className}>
      <nav className="space-y-1" style={{ padding: '0.5rem 0' }}>
        {tocItems.map((item) => (
          <button
            key={item.id}
            onClick={() => handleItemClick(item.id)}
            className={`notion-toc-item ${activeId === item.id ? 'active' : ''}`}
            style={{
              paddingLeft: `${12 + (item.level - 1) * 16}px`,
              paddingRight: '12px',
              paddingTop: '8px',
              paddingBottom: '8px',
              width: '100%',
              textAlign: 'left',
              background: 'none',
              border: 'none',
              color: activeId === item.id ? '#16a34a' : '#6b7280',
              fontSize: '13px',
              lineHeight: 1.4,
              cursor: 'pointer',
              borderRadius: '6px',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={(e) => {
              if (activeId !== item.id) {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
                e.currentTarget.style.color = '#22c55e'
              }
            }}
            onMouseLeave={(e) => {
              if (activeId !== item.id) {
                e.currentTarget.style.background = 'none'
                e.currentTarget.style.color = '#6b7280'
              }
            }}
          >
            <span style={{ 
              display: 'block',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap'
            }}>
              {item.text}
            </span>
          </button>
        ))}
      </nav>
    </div>
  )
}