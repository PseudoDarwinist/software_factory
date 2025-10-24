import React, { useEffect, useMemo, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { missionControlApi } from '@/services/api/missionControlApi'
import { Block } from '@/lib/blocks/types'
import { editorJsToBlocks, markdownToBlocks, jsonToBlocks, jsonishPrdToBlocks } from '@/lib/blocks/convert'
import { BlockRenderer } from '@/components/prd/BlockRenderer'
import { NautexDocumentTree } from '@/components/prd/NautexDocumentTree'
import { AIChatPanel } from '@/components/prd/AIChatPanel'
import { NautexProgressIndicator, NautexTypingIndicator, NautexSuccessToast } from '@/components/prd/NautexProgressIndicator'
import { usePRDSession, usePRDSessionActions } from '@/stores/missionControlStore'
import '@/components/prd/nautex-animations.css'

export const PRDEditor: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [search] = useSearchParams()
  const prdId = search.get('prd') || undefined
  const version = search.get('version') || undefined
  
  // Use persistent store for PRD session data
  const prdSessionActions = usePRDSessionActions()
  const storedSession = usePRDSession(sessionId || null)
  
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [blocks, setBlocks] = useState<Block[]>([])
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [hasUnreadMessages, setHasUnreadMessages] = useState(false)
  const [leftPanelWidth, setLeftPanelWidth] = useState(240)
  const [rightPanelWidth, setRightPanelWidth] = useState(400)
  const [isLeftPanelCollapsed, setIsLeftPanelCollapsed] = useState(false)
  const [generationProgress, setGenerationProgress] = useState(0)
  const [generationStage, setGenerationStage] = useState<'idle' | 'processing' | 'completed' | 'updating'>('idle')
  const [isAiTyping, setIsAiTyping] = useState(false)
  const [showSuccessToast, setShowSuccessToast] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true)
        setError(null)
        
        // First try to load from stored session if available
        if (storedSession && storedSession.prdContent) {
          console.log('[PRDEditor] Loading from stored session:', storedSession.sessionId)
          const maybeJson = typeof storedSession.prdContent === 'string' && /[{}\[\]]/.test(storedSession.prdContent)
          if (maybeJson) {
            const asBlocks = jsonToBlocks(storedSession.prdContent)
            console.log('[PRDEditor] Converted stored PRD content to blocks:', asBlocks.length)
            if (asBlocks.length > 1) {
              setBlocks(asBlocks)
              setLoading(false)
              return
            }
          } else {
            const asBlocks = markdownToBlocks(storedSession.prdContent)
            setBlocks(asBlocks)
            setLoading(false)
            return
          }
        }

        // Prefer PRD id when available; otherwise use session id (backend supports latest for session)
        const idOrSession = prdId || sessionId!
        const res = await missionControlApi.getPrdEditorContent(idOrSession, version || undefined)
        const dataPart = (res as any)?.data || res
        const blocksV1 = (dataPart as any)?.blocks
        const ej = (dataPart as any)?.editorjs_content
        const mdPreview = (dataPart as any)?.markdown

        console.log('[PRDEditor] load result keys:', Object.keys(dataPart || {}))
        if (Array.isArray(blocksV1) && blocksV1.length) {
          console.log('[PRDEditor] using server-supplied blocks v1:', blocksV1.length)
          setBlocks(blocksV1)
        } else if (ej && ej.blocks) {
          console.log('[PRDEditor] using editorjs_content path; blocks:', Array.isArray(ej.blocks) ? ej.blocks.length : typeof (ej as any).blocks)
          try { console.log('[PRDEditor] first editorjs block:', JSON.stringify(ej.blocks?.[0])?.slice(0,240)) } catch {}
          const conv = editorJsToBlocks(ej)
          console.log('[PRDEditor] converted editorjs → blocks:', conv.length)
          setBlocks(conv)
        } else if (mdPreview) {
          // Many earlier flows return a JSON-structured PRD preview; detect & convert
          const maybeJson = typeof mdPreview === 'string' && /[{}\[\]]/.test(mdPreview)
          if (maybeJson) {
            const asBlocks = jsonToBlocks(mdPreview)
            // Heuristic: if conversion produced more than one block, use it; otherwise fallback to markdown
            console.log('[PRDEditor] markdown field looked like JSON; blocks:', asBlocks.length)
            try { console.log('[PRDEditor] markdown preview sample:', String(mdPreview).slice(0, 240)) } catch {}
            if (asBlocks.length > 1) setBlocks(asBlocks)
            else setBlocks(markdownToBlocks(mdPreview))
          } else {
            setBlocks(markdownToBlocks(mdPreview))
          }
        } else {
          // Try session context preview as a last resort
          if (sessionId) {
            const ctx = await missionControlApi.getSessionContext(sessionId)
            if (ctx?.prd_preview) {
              const pv = ctx.prd_preview
              
              // Update or create session in store with PRD content
              if (storedSession) {
                prdSessionActions.updatePRDSession(sessionId, {
                  prdContent: pv,
                  status: 'ready'
                })
              } else {
                prdSessionActions.createPRDSession({
                  sessionId: sessionId,
                  projectId: ctx.project_id || 'unknown',
                  description: ctx.description || 'PRD Session',
                  status: 'ready',
                  files: [],
                  prdContent: pv
                })
              }
              
              const maybeJson2 = typeof pv === 'string' && /[{}\[\]]/.test(pv)
              if (maybeJson2) {
                const asBlocks = jsonToBlocks(pv)
                console.log('[PRDEditor] session context preview looked like JSON; blocks:', asBlocks.length)
                try { console.log('[PRDEditor] session preview sample:', String(pv).slice(0, 240)) } catch {}
                if (asBlocks.length > 1) setBlocks(asBlocks)
                else setBlocks(markdownToBlocks(pv))
              } else {
                setBlocks(markdownToBlocks(pv))
              }
            }
          }
        }
      } catch (e: any) {
        setError(e?.message || 'Failed to load PRD')
        console.error('[PRDEditor] load error:', e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [sessionId, prdId, version, storedSession?.prdContent])

  // Final guard: if we somehow still have one giant JSON paragraph, convert before render
  const displayBlocks = useMemo(() => {
    if (!blocks || blocks.length !== 1) return blocks
    const only = blocks[0]
    if (only.type === 'paragraph') {
      const txt = (only as any).content?.text || ''
      const looksJson = typeof txt === 'string' && /[\{\[]/.test(txt) && txt.length > 40
      if (looksJson) {
        try {
          let parsed = jsonToBlocks(txt)
          if (!parsed || parsed.length <= 1) {
            parsed = jsonishPrdToBlocks(txt)
          }
          console.log('[PRDEditor] final guard converted JSON-ish to', parsed.length, 'blocks')
          return parsed
        } catch {
          return blocks
        }
      }
    }
    return blocks
  }, [blocks])

  // Extract document title from blocks or use a clean default
  const title = useMemo(() => {
    const headerBlock = displayBlocks.find(block => block.type === 'header' && (block.content as any)?.level === 1)
    if (headerBlock) {
      return (headerBlock.content as any).text
    }
    return 'Product Specification'
  }, [displayBlocks])

  return (
    <div style={{ height: '100vh', background: '#ffffff', color: '#1f2937', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <header style={{ 
        height: '60px', 
        flexShrink: 0,
        backdropFilter: 'blur(10px)', 
        background: 'rgba(255,255,255,0.98)', 
        borderBottom: '1px solid rgba(229,231,235,0.8)',
        display: 'flex',
        alignItems: 'center',
        padding: '0 2rem',
        zIndex: 10,
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
      }}>
        <div style={{ flex: 1 }}>
          <h1 style={{ margin: 0, fontSize: 18, letterSpacing: 0.2, fontWeight: 600, color: '#1f2937' }}>{title}</h1>
        </div>
      </header>

      {/* Main application area */}
      <div style={{ 
        flex: 1, 
        display: 'flex', 
        overflow: 'hidden',
        position: 'relative'
      }}>
        {/* Left Panel - File Structure & Navigation */}
        <aside className="nautex-tree" style={{ 
          width: isLeftPanelCollapsed ? 48 : leftPanelWidth, 
          flexShrink: 0,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          borderRight: '1px solid #e5e7eb',
          background: '#fafafa',
          transition: 'width 0.2s ease'
        }}>
          <div style={{ 
            padding: isLeftPanelCollapsed ? '1rem 0.5rem' : '1rem', 
            borderBottom: '1px solid rgba(229, 231, 235, 0.6)',
            flexShrink: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            {!isLeftPanelCollapsed && (
              <div style={{ fontSize: 12, fontWeight: 600, color: '#16a34a', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                STRUCTURE
              </div>
            )}
            <button
              onClick={() => setIsLeftPanelCollapsed(!isLeftPanelCollapsed)}
              style={{
                background: 'none',
                border: 'none',
                padding: '4px',
                cursor: 'pointer',
                borderRadius: '4px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#6b7280',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#e5e7eb'
                e.currentTarget.style.color = '#374151'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'none'
                e.currentTarget.style.color = '#6b7280'
              }}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path 
                  d={isLeftPanelCollapsed ? 'M6 4L10 8L6 12' : 'M10 4L6 8L10 12'} 
                  stroke="currentColor" 
                  strokeWidth="2" 
                  strokeLinecap="round" 
                  strokeLinejoin="round"
                />
              </svg>
            </button>
          </div>
          {!isLeftPanelCollapsed && (
            <div style={{ flex: 1, overflow: 'auto', padding: '0.5rem' }}>
              <NautexDocumentTree blocks={displayBlocks} title={title} />
            </div>
          )}
        </aside>

        {/* Left Panel Resize Handle */}
        {!isLeftPanelCollapsed && (
          <div
            style={{
              width: '4px',
              cursor: 'col-resize',
              background: 'transparent',
              position: 'relative',
              flexShrink: 0
            }}
            onMouseDown={(e) => {
              e.preventDefault()
              const startX = e.clientX
              const startWidth = leftPanelWidth
              
              const handleMouseMove = (e: MouseEvent) => {
                const newWidth = Math.max(200, Math.min(500, startWidth + (e.clientX - startX)))
                setLeftPanelWidth(newWidth)
              }
              
              const handleMouseUp = () => {
                document.removeEventListener('mousemove', handleMouseMove)
                document.removeEventListener('mouseup', handleMouseUp)
              }
              
              document.addEventListener('mousemove', handleMouseMove)
              document.addEventListener('mouseup', handleMouseUp)
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#3b82f6'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent'
            }}
          >
            <div style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: '3px',
              height: '30px',
              background: '#d1d5db',
              borderRadius: '2px'
            }} />
          </div>
        )}
        
        {/* Main Content Area */}
        <main style={{ 
          flex: 1, 
          overflow: 'auto',
          background: '#ffffff',
          position: 'relative',
          minWidth: 0
        }}>
          <div style={{ 
            maxWidth: 'none',
            padding: '2rem 3rem',
            minHeight: '100%'
          }}>
            {loading && (
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                height: '200px',
                color: '#16a34a'
              }}>
                Loading PRD…
              </div>
            )}
            {error && (
              <div style={{ 
                color: '#dc2626', 
                marginBottom: '2rem',
                padding: '1rem',
                background: 'rgba(248, 113, 113, 0.1)',
                border: '1px solid rgba(248, 113, 113, 0.2)',
                borderRadius: '8px'
              }}>
                {error}
              </div>
            )}
            {!loading && !error && (
              <BlockRenderer blocks={displayBlocks} sessionId={sessionId} />
            )}
          </div>
        </main>

        {/* Right Panel Resize Handle */}
        {isChatOpen && (
          <div
            style={{
              width: '4px',
              cursor: 'col-resize',
              background: 'transparent',
              position: 'relative',
              flexShrink: 0
            }}
            onMouseDown={(e) => {
              e.preventDefault()
              const startX = e.clientX
              const startWidth = rightPanelWidth
              
              const handleMouseMove = (e: MouseEvent) => {
                const newWidth = Math.max(300, Math.min(800, startWidth - (e.clientX - startX)))
                setRightPanelWidth(newWidth)
              }
              
              const handleMouseUp = () => {
                document.removeEventListener('mousemove', handleMouseMove)
                document.removeEventListener('mouseup', handleMouseUp)
              }
              
              document.addEventListener('mousemove', handleMouseMove)
              document.addEventListener('mouseup', handleMouseUp)
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#3b82f6'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent'
            }}
          >
            <div style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              width: '3px',
              height: '30px',
              background: '#d1d5db',
              borderRadius: '2px'
            }} />
          </div>
        )}

        {/* Right Panel - AI Chat */}
        {isChatOpen && (
          <aside style={{
            width: rightPanelWidth,
            flexShrink: 0,
            borderLeft: '1px solid #e5e7eb',
            background: '#ffffff',
            display: 'flex',
            flexDirection: 'column'
          }}>
            <AIChatPanel 
              isOpen={true}
              onClose={() => setIsChatOpen(false)}
              sessionId={sessionId}
              currentBlocks={displayBlocks}
              onBlocksUpdate={(newBlocks) => {
                setBlocks(newBlocks)
                // Also update the store with the new blocks content
                if (sessionId && storedSession) {
                  // Convert blocks back to JSON for storage
                  const blocksContent = JSON.stringify(newBlocks)
                  prdSessionActions.updatePRDSession(sessionId, {
                    prdContent: blocksContent
                  })
                }
              }}
              onPRDUpdate={(content) => {
                console.log('PRD update from AI:', content)
                setGenerationStage('processing')
                setIsAiTyping(true)
                setGenerationProgress(0)
                
                // Update the store with new content
                if (sessionId && storedSession) {
                  prdSessionActions.updatePRDSession(sessionId, {
                    prdContent: content,
                    status: 'ready'
                  })
                }
                
                const progressInterval = setInterval(() => {
                  setGenerationProgress(prev => {
                    const next = prev + Math.random() * 15
                    if (next >= 100) {
                      clearInterval(progressInterval)
                      setGenerationStage('completed')
                      setIsAiTyping(false)
                      setShowSuccessToast(true)
                      setTimeout(() => setGenerationStage('idle'), 2000)
                      return 100
                    }
                    return next
                  })
                }, 200)
              }}
              isIntegratedPanel={true}
            />
          </aside>
        )}
      </div>

      {/* Floating Chat Button - Only show when chat is closed */}
      {!isChatOpen && (
        <button
          onClick={() => setIsChatOpen(true)}
          style={{
            position: 'fixed',
            bottom: '2rem',
            right: '2rem',
            width: '60px',
            height: '60px',
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #16a34a, #22c55e)',
            border: 'none',
            boxShadow: '0 4px 12px rgba(22, 163, 74, 0.3)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            zIndex: 50,
            transition: 'all 0.3s ease',
            transform: hasUnreadMessages ? 'scale(1.1)' : 'scale(1)'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = hasUnreadMessages ? 'scale(1.15)' : 'scale(1.05)'
            e.currentTarget.style.boxShadow = '0 6px 20px rgba(22, 163, 74, 0.4)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = hasUnreadMessages ? 'scale(1.1)' : 'scale(1)'
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(22, 163, 74, 0.3)'
          }}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path 
              d="M12 2C6.48 2 2 6.48 2 12C2 13.54 2.36 14.99 3 16.29L2 22L7.71 21C9.01 21.64 10.46 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2Z" 
              fill="currentColor"
            />
            <path 
              d="M8 10H16M8 14H13" 
              stroke="white" 
              strokeWidth="1.5" 
              strokeLinecap="round"
            />
          </svg>
          {hasUnreadMessages && (
            <div style={{
              position: 'absolute',
              top: '8px',
              right: '8px',
              width: '12px',
              height: '12px',
              background: '#ef4444',
              borderRadius: '50%',
              border: '2px solid white'
            }} />
          )}
        </button>
      )}

      {/* Nautex-style progress indicators */}
      <NautexProgressIndicator
        stage={generationStage}
        progress={generationProgress}
        text={
          generationStage === 'processing' ? 'Generating comprehensive PRD...' :
          generationStage === 'completed' ? 'PRD generation complete' :
          generationStage === 'updating' ? 'Updating document sections...' : ''
        }
        showProgress={generationStage === 'processing'}
      />

      <NautexTypingIndicator 
        user="AI Assistant"
        show={isAiTyping}
      />

      <NautexSuccessToast
        message="PRD updated successfully!"
        show={showSuccessToast}
        onClose={() => setShowSuccessToast(false)}
      />
    </div>
  )
}

export default PRDEditor
