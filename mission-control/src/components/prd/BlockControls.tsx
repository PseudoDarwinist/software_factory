import React, { useState, useRef, useEffect } from 'react'
import { Block } from '@/lib/blocks/types'

interface BlockControlsProps {
  block: Block
  onUpdate?: (updatedBlock: Block) => void
  onDelete?: () => void
  onAddAbove?: () => void
  onAddBelow?: () => void
  sessionId?: string
}

const PlusIcon = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <path d="M7 3V11M3 7H11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
)

const TrashIcon = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <path d="M4 5V11H10V5M5 3V2.5C5 2.22 5.22 2 5.5 2H8.5C8.78 2 9 2.22 9 2.5V3M2 4H12M6 7V9M8 7V9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
)

const DragIcon = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <circle cx="4" cy="4" r="1" fill="currentColor"/>
    <circle cx="10" cy="4" r="1" fill="currentColor"/>
    <circle cx="4" cy="10" r="1" fill="currentColor"/>
    <circle cx="10" cy="10" r="1" fill="currentColor"/>
  </svg>
)

const TypeSelector = ({ currentType, onTypeChange }: { currentType: string; onTypeChange: (type: string) => void }) => {
  const [isOpen, setIsOpen] = useState(false)
  
  const blockTypes = [
    { value: 'header', label: 'Header', icon: 'H' },
    { value: 'paragraph', label: 'Paragraph', icon: 'P' },
    { value: 'bullet-list', label: 'Bullet List', icon: '•' },
    { value: 'numbered-list', label: 'Numbered List', icon: '1.' },
    { value: 'code', label: 'Code', icon: '</>' },
    { value: 'mermaid-diagram', label: 'Diagram', icon: '📊' },
  ]

  const currentTypeInfo = blockTypes.find(t => t.value === currentType) || blockTypes[1]

  return (
    <div className="relative">
      <button
        className="flex items-center gap-1 px-2 py-1 text-xs rounded hover:bg-white/10 transition-colors"
        onClick={() => setIsOpen(!isOpen)}
        style={{ color: '#6b7280' }}
      >
        <span>{currentTypeInfo.icon}</span>
        <span>{currentTypeInfo.label}</span>
      </button>
      
      {isOpen && (
        <div
          className="absolute top-full left-0 mt-1 bg-gray-900 border rounded-lg shadow-lg z-50 min-w-32"
          style={{ 
            borderColor: 'rgba(255,255,255,0.08)',
            background: 'rgba(12, 17, 25, 0.95)',
            backdropFilter: 'blur(8px)'
          }}
        >
          {blockTypes.map((type) => (
            <button
              key={type.value}
              className="w-full flex items-center gap-2 px-3 py-2 text-xs hover:bg-white/10 first:rounded-t-lg last:rounded-b-lg text-left"
              onClick={() => {
                onTypeChange(type.value)
                setIsOpen(false)
              }}
              style={{ color: '#16a34a' }}
            >
              <span className="w-4">{type.icon}</span>
              <span>{type.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export const BlockControls: React.FC<BlockControlsProps> = ({
  block,
  onUpdate,
  onDelete,
  onAddAbove,
  onAddBelow,
  sessionId
}) => {
  const [isVisible, setIsVisible] = useState(false)
  const [position, setPosition] = useState({ x: 0, y: 0 })
  const controlsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const blockElement = document.querySelector(`[data-block-id="${block.id}"]`)
    if (!blockElement) return

    const handleMouseEnter = (e: MouseEvent) => {
      const rect = blockElement.getBoundingClientRect()
      setPosition({ 
        x: rect.left - 80, // Position to the left of the block
        y: rect.top 
      })
      setIsVisible(true)
    }

    const handleMouseLeave = (e: MouseEvent) => {
      // Don't hide if mouse is over the controls
      const relatedTarget = e.relatedTarget as HTMLElement
      if (controlsRef.current?.contains(relatedTarget)) return
      
      setTimeout(() => setIsVisible(false), 100) // Small delay to allow moving to controls
    }

    blockElement.addEventListener('mouseenter', handleMouseEnter)
    blockElement.addEventListener('mouseleave', handleMouseLeave)

    return () => {
      blockElement.removeEventListener('mouseenter', handleMouseEnter)
      blockElement.removeEventListener('mouseleave', handleMouseLeave)
    }
  }, [block.id])

  if (!isVisible) return null

  const handleTypeChange = (newType: string) => {
    if (onUpdate && newType !== block.type) {
      // Create appropriate content for the new type
      let newContent
      switch (newType) {
        case 'header':
          newContent = { level: 2, text: 'New Header' }
          break
        case 'paragraph':
          newContent = { text: 'New paragraph' }
          break
        case 'bullet-list':
        case 'numbered-list':
          newContent = { items: ['New item'] }
          break
        case 'code':
          newContent = { language: '', code: '// New code block' }
          break
        case 'mermaid-diagram':
          newContent = { code: 'flowchart TD\n    A[Start] --> B[End]' }
          break
        default:
          newContent = { text: 'New content' }
      }

      const updatedBlock = {
        ...block,
        type: newType,
        content: newContent
      }
      onUpdate(updatedBlock)
    }
  }

  return (
    <div
      ref={controlsRef}
      className="fixed z-50 flex items-center gap-1 p-1 rounded-lg shadow-lg"
      style={{
        left: position.x,
        top: position.y,
        background: 'rgba(12, 17, 25, 0.95)',
        border: '1px solid rgba(255,255,255,0.08)',
        backdropFilter: 'blur(8px)',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
      }}
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
    >
      {/* Drag handle */}
      <button 
        className="p-1 rounded hover:bg-white/10 transition-colors cursor-grab"
        style={{ color: '#6b7280' }}
        title="Drag to reorder"
      >
        <DragIcon />
      </button>

      {/* Type selector */}
      <TypeSelector currentType={block.type} onTypeChange={handleTypeChange} />

      {/* Add above */}
      <button 
        className="p-1 rounded hover:bg-white/10 transition-colors"
        onClick={onAddAbove}
        style={{ color: '#6b7280' }}
        title="Add block above"
      >
        <PlusIcon />
      </button>

      {/* Delete */}
      <button 
        className="p-1 rounded hover:bg-white/10 hover:text-red-400 transition-colors"
        onClick={onDelete}
        style={{ color: '#6b7280' }}
        title="Delete block"
      >
        <TrashIcon />
      </button>
    </div>
  )
}