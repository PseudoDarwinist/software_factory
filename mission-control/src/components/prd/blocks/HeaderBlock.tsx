import React, { useState, useRef, useEffect } from 'react'
import { HeaderContent } from '@/lib/blocks/types'
import '../notion-styles.css'

export const HeaderBlock: React.FC<{ 
  content: HeaderContent; 
  blockId?: string;
  onUpdate?: (content: HeaderContent) => void;
  isEditable?: boolean;
}> = ({ content, blockId, onUpdate, isEditable = true }) => {
  const [isEditing, setIsEditing] = useState(false)
  const [editText, setEditText] = useState(content.text)
  const inputRef = useRef<HTMLInputElement>(null)
  
  const Tag = (`h${content.level}` as unknown) as keyof JSX.IntrinsicElements

  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.focus()
      inputRef.current.select()
    }
  }, [isEditing])

  const handleClick = () => {
    if (isEditable) {
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
    if (e.key === 'Enter') {
      handleSave()
    } else if (e.key === 'Escape') {
      setEditText(content.text)
      setIsEditing(false)
    }
  }

  const handleBlur = () => {
    handleSave()
  }

  if (isEditing) {
    return (
      <input
        ref={inputRef}
        data-block-id={blockId}
        value={editText}
        onChange={(e) => setEditText(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        style={{
          margin: '0.75rem 0',
          lineHeight: 1.25,
          background: 'transparent',
          border: '2px solid #15F1CC',
          borderRadius: '4px',
          padding: '4px 8px',
          color: 'inherit',
          fontSize: 'inherit',
          fontWeight: 'inherit',
          fontFamily: 'inherit',
          width: '100%',
          outline: 'none'
        }}
        className="notion-input"
      />
    )
  }

  return (
    <Tag 
      data-block-id={blockId}
      onClick={handleClick}
      style={{ 
        margin: '0.75rem 0', 
        lineHeight: 1.25,
        cursor: isEditable ? 'text' : 'default',
        padding: '4px 8px',
        borderRadius: '4px',
        transition: 'background-color 0.2s'
      }}
      className="notion-block hover:bg-white/5"
    >
      {content.text}
    </Tag>
  )
}

