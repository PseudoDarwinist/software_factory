import React, { useEffect, useMemo, useRef, useState } from 'react'
import type { Block } from '@/lib/blocks/types'

interface DiagramBlockProps {
  block: Block
  onUpdate?: (block: Block) => void
}

export const DiagramBlock: React.FC<DiagramBlockProps> = ({ block, onUpdate }) => {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const previewRef = useRef<HTMLDivElement | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)
  
  const [error, setError] = useState<string | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [editCode, setEditCode] = useState('')
  const [previewError, setPreviewError] = useState<string | null>(null)
  
  const code: string = (block as any).content?.code || ''
  const diagramType: string | undefined = (block as any).content?.diagramType

  const normalizeMermaid = (src: string) => {
    let c = (src || '').replace(/\r/g, '').trim()
    // Ensure newline after directive
    c = c.replace(/^(graph|flowchart)\s+([A-Za-z]+)\s+/, '$1 $2\n')
    c = c.replace(/^classDiagram\s+/, 'classDiagram\n')
    c = c.replace(/^erDiagram\s+/, 'erDiagram\n')
    // Insert newlines between statements and at edges
    c = c.replace(/(\]|\)|\})\s+([A-Za-z][A-Za-z0-9_]*)/g, '$1\n$2')
    c = c.replace(/\s([A-Za-z][A-Za-z0-9_]*)\s*(\[|\(|\{)/g, '\n$1$2')
    c = c.replace(/\s([A-Za-z][A-Za-z0-9_]*)\s*--/g, '\n$1--')
    // Class members formatting
    c = c.replace(/\{\s*\+/g, '{\n  +')
    c = c.replace(/;\s*\+/g, ';\n  +')
    // Multiple class declarations on one line
    c = c.replace(/\s+class\s+/g, '\nclass ')
    return c
  }

  const id = useMemo(() => `mmd-${block.id}`, [block.id])
  const previewId = useMemo(() => `mmd-preview-${block.id}`, [block.id])

  // Initialize edit code when entering edit mode
  useEffect(() => {
    if (isEditing && !editCode) {
      setEditCode(code)
    }
  }, [isEditing, code, editCode])

  // Render main diagram
  useEffect(() => {
    if (isEditing) return // Don't render main diagram in edit mode
    
    let cancelled = false
    const render = async () => {
      if (cancelled) return
      setError(null)
      try {
        // Lazy import; fallback gracefully if package not installed
        const lib = await import('mermaid').catch(() => null as any)
        if (!lib || !lib.default) throw new Error('Mermaid not available')
        const mermaid = lib.default
        mermaid.initialize({ startOnLoad: false, securityLevel: 'loose', theme: 'dark' })
        const el = containerRef.current
        if (!el || cancelled) return
        const tryRender = async (src: string) => (await mermaid.render(id + '-svg', src)).svg
        let svg = ''
        try {
          svg = await tryRender(code)
        } catch (e1: any) {
          const normalized = normalizeMermaid(code)
          try {
            svg = await tryRender(normalized)
          } catch (e2: any) {
            throw new Error(e2?.message || e1?.message || 'Invalid diagram syntax')
          }
        }
        if (cancelled) return
        el.innerHTML = svg
      } catch (e: any) {
        if (!cancelled) {
          setError(e?.message || 'Failed to render diagram')
        }
      }
    }
    render()
    return () => { cancelled = true }
  }, [code, id, isEditing])

  // Render preview diagram in edit mode
  useEffect(() => {
    if (!isEditing || !editCode.trim()) return
    
    let cancelled = false
    const renderPreview = async () => {
      if (cancelled) return
      setPreviewError(null)
      try {
        const lib = await import('mermaid').catch(() => null as any)
        if (!lib || !lib.default) throw new Error('Mermaid not available')
        const mermaid = lib.default
        mermaid.initialize({ startOnLoad: false, securityLevel: 'loose', theme: 'dark' })
        const el = previewRef.current
        if (!el || cancelled) return
        const tryRender = async (src: string) => (await mermaid.render(previewId + '-svg', src)).svg
        let svg = ''
        try {
          svg = await tryRender(editCode)
        } catch (e1: any) {
          const normalized = normalizeMermaid(editCode)
          try {
            svg = await tryRender(normalized)
          } catch (e2: any) {
            throw new Error(e2?.message || e1?.message || 'Invalid diagram syntax')
          }
        }
        if (cancelled) return
        el.innerHTML = svg
      } catch (e: any) {
        if (!cancelled) {
          setPreviewError(e?.message || 'Invalid diagram syntax')
        }
      }
    }
    
    // Debounce preview rendering
    const timeoutId = setTimeout(renderPreview, 500)
    return () => {
      cancelled = true
      clearTimeout(timeoutId)
    }
  }, [editCode, previewId, isEditing])

  const handleEdit = () => {
    setIsEditing(true)
    setEditCode(code)
    // Focus textarea after state update
    setTimeout(() => {
      textareaRef.current?.focus()
    }, 0)
  }

  const handleUpdate = () => {
    if (onUpdate) {
      const updatedBlock = {
        ...block,
        content: {
          ...(block as any).content,
          code: editCode
        }
      }
      onUpdate(updatedBlock)
    }
    setIsEditing(false)
  }

  const handleCancel = () => {
    setEditCode(code)
    setIsEditing(false)
    setPreviewError(null)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Tab') {
      e.preventDefault()
      const textarea = e.target as HTMLTextAreaElement
      const start = textarea.selectionStart
      const end = textarea.selectionEnd
      const newValue = editCode.substring(0, start) + '  ' + editCode.substring(end)
      setEditCode(newValue)
      // Set cursor position after the inserted spaces
      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 2
      }, 0)
    }
  }

  if (isEditing) {
    return (
      <div style={{ 
        padding: '0.75rem', 
        border: '1px solid #444', 
        borderRadius: 8, 
        margin: '0.5rem 0',
        backgroundColor: '#f8fafc'
      }}>
        <div style={{ 
          fontSize: 12, 
          opacity: 0.7, 
          marginBottom: 8,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span>Edit Mermaid Diagram{diagramType ? ` • ${diagramType}` : ''}</span>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              onClick={handleUpdate}
              style={{
                padding: '4px 12px',
                fontSize: '12px',
                backgroundColor: '#0066cc',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Update Diagram
            </button>
            <button
              onClick={handleCancel}
              style={{
                padding: '4px 12px',
                fontSize: '12px',
                backgroundColor: '#666',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>
          </div>
        </div>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          {/* Code Editor */}
          <div>
            <div style={{ fontSize: '11px', opacity: 0.6, marginBottom: '4px' }}>Code</div>
            <textarea
              ref={textareaRef}
              value={editCode}
              onChange={(e) => setEditCode(e.target.value)}
              onKeyDown={handleKeyDown}
              style={{
                width: '100%',
                height: '200px',
                padding: '8px',
                backgroundColor: '#ffffff',
                color: '#1f2937',
                border: '1px solid #30363d',
                borderRadius: '4px',
                fontFamily: 'Menlo, Monaco, "Courier New", monospace',
                fontSize: '13px',
                lineHeight: '1.4',
                resize: 'vertical',
                outline: 'none'
              }}
              placeholder="Enter Mermaid diagram code..."
            />
          </div>
          
          {/* Preview */}
          <div>
            <div style={{ fontSize: '11px', opacity: 0.6, marginBottom: '4px' }}>Preview</div>
            <div style={{
              height: '200px',
              border: '1px solid #30363d',
              borderRadius: '4px',
              backgroundColor: '#ffffff',
              padding: '8px',
              overflow: 'auto'
            }}>
              {previewError ? (
                <div style={{ color: '#ff8a8a', fontSize: '12px' }}>
                  <div style={{ marginBottom: '6px' }}>Preview error: {previewError}</div>
                </div>
              ) : editCode.trim() ? (
                <div ref={previewRef} id={previewId} />
              ) : (
                <div style={{ color: '#666', fontSize: '12px', fontStyle: 'italic' }}>
                  Enter code to see preview...
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div 
      data-block-id={block.id}
      style={{ 
        padding: '0.75rem', 
        border: '1px dashed #333', 
        borderRadius: 8, 
        margin: '0.5rem 0',
        cursor: 'pointer'
      }}
      onClick={handleEdit}
    >
      <div style={{ 
        fontSize: 12, 
        opacity: 0.7, 
        marginBottom: 4,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <span>Mermaid{diagramType ? ` • ${diagramType}` : ''}</span>
        <span style={{ fontSize: '10px', opacity: 0.5 }}>Click to edit</span>
      </div>
      {error ? (
        <div style={{ color: '#ff8a8a' }}>
          <div style={{ marginBottom: 6 }}>Diagram error: {error}</div>
          <pre style={{ 
            whiteSpace: 'pre-wrap',
            fontFamily: 'Menlo, Monaco, "Courier New", monospace',
            fontSize: '12px',
            backgroundColor: '#f8fafc',
            padding: '8px',
            borderRadius: '4px',
            overflow: 'auto'
          }}>{code}</pre>
        </div>
      ) : (
        <div ref={containerRef} id={id} />
      )}
    </div>
  )
}
