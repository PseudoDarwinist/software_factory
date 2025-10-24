import React, { useState, useRef, useEffect } from 'react'
import { ParagraphContent } from '@/lib/blocks/types'
import '../notion-styles.css'

export const ParagraphBlock: React.FC<{ 
  content: ParagraphContent; 
  blockId?: string;
  onUpdate?: (content: ParagraphContent) => void;
  isEditable?: boolean;
}> = ({ content, blockId, onUpdate, isEditable = true }) => {
  const [isEditing, setIsEditing] = useState(false)
  const [editText, setEditText] = useState(content.text)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.focus()
      textareaRef.current.select()
      // Auto-resize textarea
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px'
    }
  }, [isEditing])

  const handleClick = () => {
    if (isEditable && !isEditing) {
      setIsEditing(true)
    }
  }

  const handleSave = () => {
    setIsEditing(false)
    if (editText !== content.text && onUpdate) {
      onUpdate({ ...content, text: editText })
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSave()
    } else if (e.key === 'Escape') {
      setEditText(content.text)
      setIsEditing(false)
    }
  }

  const handleBlur = () => {
    handleSave()
  }

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setEditText(e.target.value)
    // Auto-resize
    e.target.style.height = 'auto'
    e.target.style.height = e.target.scrollHeight + 'px'
  }

  if (isEditing) {
    return (
      <textarea
        ref={textareaRef}
        data-block-id={blockId}
        value={editText}
        onChange={handleTextChange}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        style={{
          margin: '0.5rem 0',
          color: 'var(--text-strong, #1f2937)',
          background: 'transparent',
          border: '2px solid #15F1CC',
          borderRadius: '4px',
          padding: '8px 12px',
          fontSize: 'inherit',
          fontFamily: 'inherit',
          width: '100%',
          outline: 'none',
          resize: 'none',
          minHeight: '24px'
        }}
        placeholder="Type something..."
        className="notion-textarea"
      />
    )
  }

  return (
    <p 
      data-block-id={blockId}
      onClick={handleClick}
      style={{ 
        margin: '0.5rem 0', 
        color: 'var(--text-strong, #1f2937)',
        cursor: isEditable ? 'text' : 'default',
        padding: '8px 12px',
        borderRadius: '4px',
        transition: 'background-color 0.2s',
        minHeight: '24px'
      }}
      className="notion-block hover:bg-white/5"
    >
      {content.text || <span style={{ opacity: 0.5 }}>Empty paragraph</span>}
    </p>
  )
}

