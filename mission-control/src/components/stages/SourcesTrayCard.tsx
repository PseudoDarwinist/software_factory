/**
 * SourcesTrayCard - Pixel-perfect futuristic glass UI component
 * Matches the exact specification for the Think → Refinery screen
 */

import React, { useState, useCallback, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { missionControlApi } from '@/services/api/missionControlApi'

// Types
interface FileItem {
  name: string
  type: 'pdf' | 'video' | 'image' | 'document' | 'link'
  progress: number // 0-1
  error?: string
}

interface PRDSummary {
  problem: { text: string; sources: string[] }
  audience: { text: string; sources: string[] }
  goals: { items: string[]; sources: string[] }
  risks: { items: string[]; sources: string[] }
  competitive_scan: { items: string[]; sources: string[] }
  open_questions: { items: string[]; sources: string[] }
}

interface SourceQuote {
  sourceId: string
  quote: string
  filename: string
}

interface SourcesTrayCardProps {
  status?: 'idle' | 'uploading' | 'analyzing' | 'drafting' | 'ready'
  files?: FileItem[]
  projectId?: string
  onFileAdd?: (files: File[]) => void
  onLinkAdd?: (url: string) => void
  onFileRemove?: (index: number) => void
  onAnalyze?: () => void
  onFreezePRD?: () => void
  onUploadComplete?: (sessionId: string) => void

}

// Icons as SVG components
const PlusIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M8 3V13M3 8H13" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
)

const ChevronRightIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M6 12L10 8L6 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

const FileIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <path d="M9 1H3C2.4 1 2 1.4 2 2V14C2 14.6 2.4 15 3 15H13C13.6 15 14 14.6 14 14V6L9 1Z" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M9 1V6H14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

const VideoIcon = () => (
  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
    <rect x="2" y="3" width="12" height="10" rx="2" stroke="currentColor" strokeWidth="1.5"/>
    <path d="M6 6L10 8L6 10V6Z" fill="currentColor"/>
  </svg>
)

const CloseIcon = () => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
    <path d="M9 3L3 9M3 3L9 9" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
)

// Helper function to parse AI response into structured PRD summary
const parsePRDSummary = (aiResponse: string): PRDSummary => {
  const summary: PRDSummary = {
    problem: { text: '', sources: [] },
    audience: { text: '', sources: [] },
    goals: { items: [], sources: [] },
    risks: { items: [], sources: [] },
    competitive_scan: { items: [], sources: [] },
    open_questions: { items: [], sources: [] }
  }
  
  if (!aiResponse) return summary
  
  const lines = aiResponse.split('\n')
  let currentSection: keyof PRDSummary | null = null
  
  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (!line) continue
    
    // Header detection
    if (line.startsWith('#')) {
      const normalized = line.replace(/#+\s*/, '').toLowerCase()
      if (normalized.includes('problem')) {
        currentSection = 'problem'
      } else if (normalized.includes('audience') || normalized.includes('target')) {
        currentSection = 'audience'
      } else if (normalized.includes('goal') || normalized.includes('objective')) {
        currentSection = 'goals'
      } else if (normalized.includes('risk') || normalized.includes('concern')) {
        currentSection = 'risks'
      } else if (normalized.includes('competitive') || normalized.includes('competitor')) {
        currentSection = 'competitive_scan'
      } else if (normalized.includes('question')) {
        currentSection = 'open_questions'
      } else {
        currentSection = null
      }
      continue
    }
    
    // Bullet point detection
    if (currentSection && (line.startsWith('- ') || line.startsWith('* ') || /^\d+\.\s/.test(line))) {
      const content = line.replace(/^[-*]\s*|\d+\.\s*/, '').trim()
      
      if (currentSection === 'problem' || currentSection === 'audience') {
        // Text-based sections
        const section = summary[currentSection]
        section.text += (section.text ? ' ' : '') + content
        
        // Extract source tags
        const sourceTags = content.match(/\[S\d+\]/g) || []
        sourceTags.forEach(tag => {
          if (!section.sources.includes(tag)) {
            section.sources.push(tag)
          }
        })
      } else {
        // List-based sections
        const section = summary[currentSection]
        section.items.push(content)
        
        // Extract source tags for this item
        const sourceTags = content.match(/\[S\d+\]/g) || []
        section.sources.push(sourceTags.join(', ') || '')
      }
    }
  }
  
  return summary
}

// Helper function to extract source quotes (mock implementation for now)
const extractSourceQuotes = async (sessionId: string | null): Promise<Record<string, SourceQuote>> => {
  // This would fetch actual source quotes from the backend
  // For now, return mock data
  return {
    '[S1]': {
      sourceId: 'S1',
      quote: 'Users are struggling with complex onboarding flows that take too long to complete.',
      filename: 'user_research.pdf'
    },
    '[S2]': {
      sourceId: 'S2', 
      quote: 'Market analysis shows 73% of users abandon apps during first use.',
      filename: 'market_analysis.pdf'
    },
    '[S3]': {
      sourceId: 'S3',
      quote: 'Competitive analysis reveals simpler alternatives gaining market share.',
      filename: 'competitor_research.pdf'
    }
  }
}

// PRD Summary Display Component
interface PRDSummaryDisplayProps {
  prdContent: string
  sessionId: string | null
}

const PRDSummaryDisplay: React.FC<PRDSummaryDisplayProps> = ({ prdContent, sessionId }) => {
  const [summary, setSummary] = useState<PRDSummary | null>(null)
  const [sourceQuotes, setSourceQuotes] = useState<Record<string, SourceQuote>>({})
  const [hoveredSource, setHoveredSource] = useState<string | null>(null)
  
  useEffect(() => {
    if (prdContent) {
      const parsedSummary = parsePRDSummary(prdContent)
      setSummary(parsedSummary)
      
      // Load source quotes
      extractSourceQuotes(sessionId).then(setSourceQuotes)
    }
  }, [prdContent, sessionId])
  
  if (!summary) {
    return (
      <div className="space-y-2" aria-label="Loading PRD preview">
        <div className="flex items-center gap-3">
          <span style={{ color: 'var(--text-dim)' }}>Loading PRD summary...</span>
        </div>
      </div>
    )
  }
  
  const renderSourceTag = (sourceTag: string) => {
    if (!sourceTag) return null
    
    return (
      <span
        className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ml-2 cursor-help transition-all duration-200 hover:scale-105"
        style={{
          background: 'rgba(72, 224, 216, 0.15)',
          color: 'var(--source-tag)',
          border: '1px solid rgba(72, 224, 216, 0.3)'
        }}
        onMouseEnter={() => setHoveredSource(sourceTag)}
        onMouseLeave={() => setHoveredSource(null)}
        title={sourceQuotes[sourceTag]?.quote || `Source: ${sourceTag}`}
      >
        {sourceTag}
      </span>
    )
  }
  
  const renderTextSection = (title: string, section: { text: string; sources: string[] }) => {
    if (!section.text) return null
    
    return (
      <div className="flex items-start gap-3 relative">
        <span style={{ color: 'var(--text-strong)', minWidth: 'fit-content' }}>• {title}.</span>
        <div className="flex-1">
          <span style={{ color: 'var(--text-dim)' }}>{section.text}</span>
          {section.sources.map((source, idx) => (
            <span key={idx}>{renderSourceTag(source)}</span>
          ))}
        </div>
      </div>
    )
  }
  
  const renderListSection = (title: string, section: { items: string[]; sources: string[] }) => {
    if (section.items.length === 0) return null
    
    return (
      <div className="flex items-start gap-3">
        <span style={{ color: 'var(--text-strong)', minWidth: 'fit-content' }}>• {title}.</span>
        <div className="space-y-1 flex-1">
          {section.items.map((item, idx) => (
            <div key={idx} className="flex items-start gap-2">
              <span style={{ color: 'var(--text-dim)', fontSize: '14px' }}>–</span>
              <span style={{ color: 'var(--text-dim)' }}>{item}</span>
              {section.sources[idx] && renderSourceTag(section.sources[idx])}
            </div>
          ))}
        </div>
      </div>
    )
  }
  
  return (
    <div className="space-y-3 relative" aria-label="PRD summary">
      {renderTextSection('Problem', summary.problem)}
      {renderTextSection('Audience', summary.audience)}
      {renderListSection('Goals', summary.goals)}
      {renderListSection('Risks', summary.risks)}
      {renderListSection('Competitive scan', summary.competitive_scan)}
      {renderListSection('Open questions', summary.open_questions)}
      
      {/* Tooltip for hovered source */}
      {hoveredSource && sourceQuotes[hoveredSource] && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 10 }}
          className="absolute z-50 p-3 rounded-lg shadow-lg max-w-sm"
          style={{
            background: 'rgba(12, 17, 25, 0.95)',
            border: '1px solid rgba(72, 224, 216, 0.3)',
            backdropFilter: 'blur(12px)',
            bottom: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            marginBottom: '8px'
          }}
        >
          <div className="text-xs font-medium mb-1" style={{ color: 'var(--source-tag)' }}>
            {sourceQuotes[hoveredSource].filename}
          </div>
          <div className="text-sm" style={{ color: 'var(--text-dim)' }}>
            "{sourceQuotes[hoveredSource].quote}"
          </div>
        </motion.div>
      )}
    </div>
  )
}

export const SourcesTrayCard: React.FC<SourcesTrayCardProps> = ({
  status: propStatus,
  files: propFiles,
  projectId = 'default-project',
  onFileAdd,
  onLinkAdd,
  onFileRemove,
  onAnalyze,
  onFreezePRD,
  onUploadComplete
}) => {
  // Internal state for backend integration
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [files, setFiles] = useState<FileItem[]>(propFiles || [])
  const [status, setStatus] = useState<'idle' | 'uploading' | 'analyzing' | 'drafting' | 'ready'>(propStatus || 'idle')
  const [isDragOver, setIsDragOver] = useState(false)
  const [showLinkModal, setShowLinkModal] = useState(false)
  const [linkUrl, setLinkUrl] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [prdContent, setPrdContent] = useState<string>('')
  const statusPollingRef = useRef<NodeJS.Timeout | null>(null)

  // Create upload session when component mounts
  useEffect(() => {
    const createSession = async () => {
      try {
        const session = await missionControlApi.createUploadSession(projectId, 'Upload sources for PRD generation')
        setSessionId(session.session_id)
        console.log('Created upload session:', session.session_id)
      } catch (error) {
        console.error('Failed to create upload session:', error)
        setError('Failed to initialize upload session')
      }
    }

    createSession()

    // Cleanup polling on unmount
    return () => {
      if (statusPollingRef.current) {
        clearInterval(statusPollingRef.current)
      }
    }
  }, [projectId])

  // Progress steps
  const progressSteps = [
    { key: 'reading', label: 'Reading files', active: ['uploading', 'analyzing', 'drafting', 'ready'].includes(status) },
    { key: 'pulling', label: 'Pulling key points', active: ['analyzing', 'drafting', 'ready'].includes(status) },
    { key: 'drafting', label: 'Drafting PRD', active: ['drafting', 'ready'].includes(status) },
    { key: 'ready', label: 'Ready to review', active: ['ready'].includes(status) }
  ]

  // Start polling for file processing status
  const startStatusPolling = useCallback(() => {
    if (!sessionId || statusPollingRef.current) return

    statusPollingRef.current = setInterval(async () => {
      try {
        const uploadStatus = await missionControlApi.getUploadStatus(sessionId)
        
        // Update file statuses
        setFiles(prev => prev.map(file => {
          const statusFile = uploadStatus.files.find(sf => sf.filename === file.name)
          if (statusFile) {
            return {
              ...file,
              progress: statusFile.processing_status === 'complete' ? 1 : 
                       statusFile.processing_status === 'processing' ? 0.75 : 
                       statusFile.processing_status === 'error' ? 0 : file.progress,
              error: statusFile.processing_status === 'error' ? 'Processing failed' : undefined
            }
          }
          return file
        }))

        // Stop polling if all files are processed
        if (uploadStatus.overall_status === 'complete' || uploadStatus.overall_status === 'error') {
          if (statusPollingRef.current) {
            clearInterval(statusPollingRef.current)
            statusPollingRef.current = null
          }
        }

      } catch (error) {
        console.error('Status polling failed:', error)
      }
    }, 2000) // Poll every 2 seconds
  }, [sessionId])

  // Drag and drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  const handleDrop = useCallback(async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    const droppedFiles = Array.from(e.dataTransfer.files)
    await handleFileUpload(droppedFiles)
  }, [sessionId])

  // File input handler
  const handleFileInput = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || [])
    await handleFileUpload(selectedFiles)
  }, [sessionId])

  // Handle file upload to backend
  const handleFileUpload = useCallback(async (fileList: File[]) => {
    if (!sessionId) {
      setError('Upload session not ready')
      return
    }

    setStatus('uploading')
    setError(null)

    try {
      // Filter supported files
      const supportedFiles = fileList.filter(file => {
        const extension = file.name.split('.').pop()?.toLowerCase()
        return ['pdf', 'jpg', 'jpeg', 'png', 'gif'].includes(extension || '')
      })

      if (supportedFiles.length === 0) {
        setError('No supported files found. Please upload PDF, JPG, PNG, or GIF files.')
        setStatus('idle')
        return
      }

      // Add files to UI immediately with uploading status
      const newFiles: FileItem[] = supportedFiles.map((file) => {
        const extension = file.name.split('.').pop()?.toLowerCase()
        const fileType = extension === 'pdf' ? 'pdf' : 
                        ['jpg', 'jpeg', 'png', 'gif'].includes(extension || '') ? 'image' : 'document'
        
        return {
          name: file.name,
          type: fileType as FileItem['type'],
          progress: 0
        }
      })

      setFiles(prev => [...prev, ...newFiles])

      // Upload files to backend
      const uploadResult = await missionControlApi.uploadFiles(sessionId, supportedFiles)
      
      console.log('Upload result:', uploadResult)

      // Update file progress
      setFiles(prev => prev.map(file => {
        const uploadedFile = uploadResult.uploaded_files.find(uf => uf.filename === file.name)
        if (uploadedFile) {
          return { ...file, progress: 1 }
        }
        return file
      }))

      // Start polling for processing status
      startStatusPolling()

      if (uploadResult.errors && uploadResult.errors.length > 0) {
        setError(`Some files failed to upload: ${uploadResult.errors.join(', ')}`)
      }

      // Call original callback if provided
      onFileAdd?.(supportedFiles)

    } catch (error) {
      console.error('File upload failed:', error)
      setError('Failed to upload files. Please try again.')
      setStatus('idle')
      
      // Mark files as error
      setFiles(prev => prev.map(file => 
        file.progress === 0 ? { ...file, error: 'Upload failed' } : file
      ))
    }
  }, [sessionId, onFileAdd, startStatusPolling])

  // Link submission
  const handleLinkSubmit = useCallback(async () => {
    if (!linkUrl.trim() || !sessionId) return

    setStatus('uploading')
    setError(null)

    try {
      // Add URL to UI immediately
      const newFile: FileItem = {
        name: new URL(linkUrl).hostname,
        type: 'link',
        progress: 0
      }
      
      setFiles(prev => [...prev, newFile])

      // Upload URL to backend
      const uploadResult = await missionControlApi.uploadLinks(sessionId, [linkUrl.trim()])
      
      console.log('Link upload result:', uploadResult)

      // Update file status
      setFiles(prev => prev.map(file => {
        if (file.name === newFile.name) {
          return { ...file, progress: 1 }
        }
        return file
      }))

      if (uploadResult.errors && uploadResult.errors.length > 0) {
        setError(`Link upload failed: ${uploadResult.errors.join(', ')}`)
      }

      // Call original callback if provided
      onLinkAdd?.(linkUrl.trim())

      setLinkUrl('')
      setShowLinkModal(false)

    } catch (error) {
      console.error('Link upload failed:', error)
      setError('Failed to upload link. Please try again.')
      setStatus('idle')
      
      // Mark link as error
      setFiles(prev => prev.map(file => 
        file.name === new URL(linkUrl).hostname ? { ...file, error: 'Upload failed' } : file
      ))
    }
  }, [linkUrl, sessionId, onLinkAdd])

  // Handle analyze button click
  const handleAnalyze = useCallback(async () => {
    if (!sessionId || files.length === 0) return

    setStatus('analyzing')
    setError(null)

    try {
      // Start AI analysis
      const analysisResult = await missionControlApi.analyzeSessionFiles(sessionId, 'claude-opus-4')
      
      console.log('Analysis result:', analysisResult)

      if (analysisResult.status === 'success') {
        // Simulate processing stages for better UX
        setStatus('drafting')
        
        setTimeout(async () => {
          try {
            // Get the full session context with AI analysis
            const context = await missionControlApi.getSessionContext(sessionId)
            
            if (context.ai_analysis) {
              // Use the structured PRD preview if available, otherwise use raw AI analysis
              const prdText = context.prd_preview || context.ai_analysis
              setPrdContent(prdText)
              setStatus('ready')
              console.log('PRD generated successfully')
              

            } else {
              setError('No AI analysis available')
              setStatus('idle')
            }
          } catch (error) {
            console.error('Failed to get session context:', error)
            setError('Failed to retrieve generated PRD')
            setStatus('idle')
          }
        }, 2000) // 2 second delay for drafting stage

      } else {
        setError(analysisResult.error || 'AI analysis failed')
        setStatus('idle')
      }

      // Call original callback if provided
      onAnalyze?.()

    } catch (error) {
      console.error('PRD generation failed:', error)
      setError('Failed to generate PRD. Please try again.')
      setStatus('idle')
    }
  }, [sessionId, files.length, onAnalyze])

  // Handle freeze PRD
  const handleFreezePRD = useCallback(() => {
    if (status === 'ready' && sessionId) {
      onFreezePRD?.()
      onUploadComplete?.(sessionId)
    }
  }, [status, sessionId, onFreezePRD, onUploadComplete])

  // Get file icon
  const getFileIcon = (type: FileItem['type']) => {
    switch (type) {
      case 'video': return <VideoIcon />
      default: return <FileIcon />
    }
  }

  // Get chip background class
  const getChipBackground = (type: FileItem['type']) => {
    switch (type) {
      case 'pdf':
      case 'document':
        return 'bg-gradient-to-b from-[rgba(46,139,255,0.20)] to-[rgba(46,139,255,0.08)]'
      default:
        return 'bg-gradient-to-b from-[rgba(42,51,66,0.40)] to-[rgba(42,51,66,0.18)]'
    }
  }

  return (
    <div 
      className="sources-tray-card"
      style={{
        '--bg-0': '#0A0E12',
        '--card-bg': 'rgba(12, 17, 25, 0.62)',
        '--stroke-dim': 'rgba(255,255,255,0.08)',
        '--stroke-dash': 'rgba(255,255,255,0.14)',
        '--text-strong': '#EAF2FF',
        '--text-dim': '#8EA3B5',
        '--accent-teal': '#15F1CC',
        '--accent-cyan': '#49C9FF',
        '--accent-violet': '#8F6BFF',
        '--accent-amber': '#FFD84D',
        '--chip-blue': '#2E8BFF',
        '--chip-gray': '#2A3342',
        '--progress-idle': 'rgba(255,255,255,0.14)',
        '--progress-active': '#37B7F7',
        '--source-tag': '#48E0D8',
        '--ring-glow': '0 0 0 1px rgba(255,255,255,0.08), 0 0 18px rgba(21,241,204,0.18)',
        '--btn-glow': '0 0 0 1px rgba(255,216,77,0.35), 0 0 36px rgba(255,216,77,0.45)',
        '--grad-stroke': 'linear-gradient(90deg, rgba(21,241,204,0.35) 0%, rgba(73,201,255,0.28) 45%, rgba(143,107,255,0.28) 100%)'
      } as React.CSSProperties}
    >
      <div className="relative w-full max-w-6xl mx-auto">
        {/* Main Card */}
        <div 
          className="relative rounded-3xl p-8 backdrop-blur-2xl"
          style={{
            borderRadius: '24px',
            border: '1px solid transparent',
            background: 'linear-gradient(var(--card-bg), var(--card-bg)) padding-box, var(--grad-stroke) border-box',
            boxShadow: 'var(--ring-glow)',
            overflow: 'hidden'
          }}
        >
          {/* Overlay background */}
          <div
            className="pointer-events-none absolute inset-0 rounded-3xl"
            style={{
              zIndex: 0,
              background: 'radial-gradient(120% 100% at 50% -10%, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0) 50%), linear-gradient(180deg, rgba(0,0,0,0.10), rgba(0,0,0,0.22))'
            }}
          />
          {/* Corner auras */}
          <div
            className="pointer-events-none absolute inset-0 rounded-3xl"
            style={{
              background: `
                radial-gradient(280px 140px at 6% 6%, rgba(21,241,204,0.14), transparent 60%),
                radial-gradient(300px 140px at 94% 10%, rgba(73,201,255,0.14), transparent 60%),
                radial-gradient(340px 200px at 10% 92%, rgba(255,60,180,0.12), transparent 60%),
                radial-gradient(340px 200px at 92% 92%, rgba(143,107,255,0.14), transparent 60%)
              `,
              mixBlendMode: 'screen'
            }}
          />
          {/* Bottom neon sweep */}
          <div
            className="pointer-events-none absolute left-8 right-8 bottom-4 h-px"
            style={{
              background: 'linear-gradient(90deg, rgba(255,0,200,0) 0%, rgba(255,0,200,0.55) 40%, rgba(255,0,200,0.28) 70%, rgba(255,0,200,0) 100%)',
              boxShadow: '0 0 24px rgba(255,0,200,0.35)',
              opacity: 0.65
            }}
          />
          {/* Card Content */}
          <div className="relative z-10">
            {/* Header Row */}
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-3">
                <h2 
                  className="text-lg font-semibold tracking-wide"
                  style={{ 
                    color: 'var(--text-strong)',
                    letterSpacing: '0.2px'
                  }}
                >
                  Sources tray
                </h2>
                {sessionId && (
                  <span className="text-xs text-green-400">
                    Session: {sessionId.slice(0, 8)}...
                  </span>
                )}
              </div>
              
              {/* actions: Make PRD + Add (+) */}
              <div className="flex items-center gap-3">
                {/* Make PRD draft (ring-only glass capsule) */}
                <button
                  className="relative inline-flex items-center justify-center rounded-full font-semibold text-sm transition-all duration-200 hover:scale-[1.01] active:scale-[0.99] focus:outline-none"
                  style={{
                    background: 'transparent',
                    border: 'none',
                    minWidth: '172px',
                    height: '40px',
                    padding: '0 18px',
                    opacity: files.length === 0 ? 0.55 : 1,
                    pointerEvents: files.length === 0 ? 'none' : 'auto'
                  }}
                  onClick={handleAnalyze}
                  aria-disabled={files.length === 0}
                  title={files.length === 0 ? 'Add sources to enable' : 'Generate PRD draft from sources'}
                >
                  {/* gradient ring only (cyan → teal) */}
                  <span
                    className="pointer-events-none absolute inset-0 rounded-full"
                    style={{
                      padding: '1.5px',
                      borderRadius: 9999,
                      background:
                        'linear-gradient(90deg, rgba(73,201,255,0.75), rgba(21,241,204,0.60))',
                      WebkitMask:
                        'linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)',
                      WebkitMaskComposite: 'xor',
                      maskComposite: 'exclude',
                      boxShadow: '0 0 14px rgba(73,201,255,0.22), 0 0 12px rgba(21,241,204,0.18)'
                    } as React.CSSProperties}
                  />
                  {/* faint top specular highlight */}
                  <span
                    className="pointer-events-none absolute inset-0 rounded-full"
                    style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.10)' }}
                  />
                  <span className="relative z-10" style={{ color: '#CFEFFF', letterSpacing: '0.2px' }}>
                    Make PRD draft
                  </span>
                </button>
                
                {/* existing + Add source button */}
                <button
                  className="w-9 h-9 rounded-full flex items-center justify-center transition-all duration-200 hover:scale-105"
                  style={{
                    border: '1px solid transparent',
                    background: 'linear-gradient(rgba(20,24,36,0.72), rgba(20,24,36,0.72)) padding-box, var(--grad-stroke) border-box',
                    boxShadow: 'var(--ring-glow)',
                    color: 'var(--text-strong)',
                    filter: 'saturate(0.9)'
                  }}
                  aria-label="Add source"
                  onClick={() => setShowLinkModal(true)}
                >
                  <PlusIcon />
                </button>
              </div>
            </div>

            {/* Error Display */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-4 p-3 rounded-lg"
                style={{
                  background: 'rgba(255, 107, 107, 0.1)',
                  border: '1px solid rgba(255, 107, 107, 0.3)'
                }}
              >
                <div className="flex items-center space-x-2">
                  <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-red-300 text-sm">{error}</span>
                  <button 
                    onClick={() => setError(null)}
                    className="ml-auto text-red-400 hover:text-red-300"
                  >
                    <CloseIcon />
                  </button>
                </div>
              </motion.div>
            )}

            {/* Drop Zone */}
            <div
              className={`relative w-full h-[120px] rounded-2xl mb-6 flex items-center justify-center transition-all duration-300`}
              style={{
                background: 'rgba(255,255,255,0.015)',
                border: '1px dashed',
                borderColor: isDragOver ? 'rgba(255,255,255,0.28)' : 'var(--stroke-dash)',
                boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.06)'
              }}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              aria-label="Upload sources drop zone"
            >
              <p 
                className="text-sm text-center px-4"
                style={{ color: 'var(--text-dim)' }}
              >
                {isDragOver ? 'Drop to add to PRD' : 'Drop PDFs, decks, Zoom links, webpages, Figma, screenshots…'}
              </p>
              
              {/* Hidden file input */}
              <input
                type="file"
                multiple
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                onChange={handleFileInput}
                accept=".pdf,.doc,.docx,.ppt,.pptx,.jpg,.jpeg,.png,.mp4,.mov"
              />
            </div>

            {/* File Chips Row */}
            {files.length > 0 && (
              <div className="flex items-center gap-3 mb-6">
                <div className="flex gap-2 flex-wrap">
                  {files.map((file, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className={`group relative h-10 px-3 rounded-xl flex items-center gap-2 border transition-all duration-200 ${getChipBackground(file.type)}`}
                      style={{
                        borderColor: file.error ? '#FF6B6B' : 'var(--stroke-dim)',
                        color: 'var(--text-strong)'
                      }}
                    >
                      {getFileIcon(file.type)}
                      <span className="text-sm font-medium">{file.name}</span>
                      
                      {/* Progress bar */}
                      <div 
                        className="absolute bottom-0 left-0 h-0.5 rounded-b-xl transition-all duration-300"
                        style={{
                          width: `${file.progress * 100}%`,
                          background: file.progress < 1 ? 'var(--progress-active)' : 'var(--progress-idle)'
                        }}
                      />
                      
                      {/* Remove button */}
                      <button
                        className="opacity-0 group-hover:opacity-100 transition-opacity duration-200 ml-1 p-1 hover:bg-white/10 rounded"
                        onClick={() => onFileRemove?.(index)}
                      >
                        <CloseIcon />
                      </button>
                    </motion.div>
                  ))}
                </div>
                
                {/* Ghost arrow button */}
                <button
                  className="w-9 h-9 rounded-full flex items-center justify-center transition-all duration-200 hover:scale-105"
                  style={{
                    border: '1px solid transparent',
                    background: 'linear-gradient(rgba(20,24,36,0.6), rgba(20,24,36,0.6)) padding-box, var(--grad-stroke) border-box',
                    color: 'var(--text-dim)',
                    boxShadow: 'var(--ring-glow)'
                  }}
                  onClick={handleAnalyze}
                  disabled={!sessionId || files.length === 0 || status !== 'idle'}
                  aria-label="Analyze sources now"
                  title="Analyze sources"
                >
                  <ChevronRightIcon />
                </button>
                
                {/* Secondary add button */}
                <button
                  className="w-8 h-8 rounded-full flex items-center justify-center transition-all duration-200 hover:scale-105"
                  style={{
                    border: '1px solid transparent',
                    background: 'linear-gradient(rgba(20,24,36,0.6), rgba(20,24,36,0.6)) padding-box, var(--grad-stroke) border-box',
                    color: 'var(--accent-amber)',
                    boxShadow: 'var(--ring-glow)'
                  }}
                  onClick={() => setShowLinkModal(true)}
                >
                  <PlusIcon />
                </button>
              </div>
            )}

            {/* Progress Rail */}
            <div className="mb-8">
              <div className="flex items-center justify-between relative">
                {/* Progress line */}
                <div 
                  className="absolute top-1/2 left-0 right-0 h-px -translate-y-1/2"
                  style={{ background: 'linear-gradient(90deg, rgba(255,255,255,0.18), rgba(255,255,255,0.04))' }}
                />
                
                {/* Progress nodes */}
                {progressSteps.map((step, index) => (
                  <div key={step.key} className="relative flex flex-col items-center">
                    <div
                      className={`w-3 h-3 rounded-full transition-all duration-500 ${
                        step.active ? 'shadow-lg' : ''
                      }`}
                      style={{
                        background: step.active ? 'var(--progress-active)' : 'var(--progress-idle)',
                        boxShadow: step.active ? '0 0 10px var(--progress-active), 0 0 18px rgba(55,183,247,0.28)' : 'none'
                      }}
                    />
                    <span 
                      className="text-xs mt-2 whitespace-nowrap"
                      style={{ color: 'var(--text-dim)' }}
                    >
                      {step.label}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* PRD Section (always visible for design work) */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 
                  className="text-base font-semibold"
                  style={{ color: 'var(--text-strong)' }}
                >
                  PRD draft <span style={{ color: 'var(--text-dim)' }}>(live doc)</span>
                </h3>
                
                <button
                  className="group relative inline-flex items-center justify-center rounded-full font-semibold text-sm transition-all duration-200 hover:scale-[1.01] active:scale-[0.99] focus:outline-none"
                  style={{
                    background: 'transparent',
                    border: 'none',
                    minWidth: '200px',
                    height: '52px',
                    padding: '0 30px',
                    filter: 'saturate(1.02)'
                  }}
                  onClick={handleFreezePRD}
                  aria-disabled={status !== 'ready'}
                  title={status === 'ready' ? 'Freeze PRD' : 'PRD not ready yet'}
                >
                  {/* 1) Gradient ring only (masked) */}
                  <span
                    className="pointer-events-none absolute inset-0 rounded-full"
                    style={{
                      padding: '2px',
                      borderRadius: '9999px',
                      background: 'linear-gradient(90deg, rgba(255,216,77,0.92) 0%, rgba(223,255,160,0.78) 38%, rgba(21,241,204,0.70) 100%)',
                      WebkitMask: 'linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)',
                      WebkitMaskComposite: 'xor',
                      maskComposite: 'exclude',
                      boxShadow: '0 0 22px rgba(255,216,77,0.35), 0 0 28px rgba(21,241,204,0.25)'
                    } as React.CSSProperties}
                  />
                  {/* 2) Edge vignette (darkens very outer interior to sell hollowness) */}
                  <span
                    className="pointer-events-none absolute inset-[2px] rounded-full"
                    style={{
                      background: 'radial-gradient(120% 100% at 50% 50%, rgba(0,0,0,0) 60%, rgba(0,0,0,0.22) 100%)',
                      mixBlendMode: 'multiply'
                    }}
                  />
                  {/* 3) Luminous core under text (subtle, not a fill) */}
                  <span
                    className="pointer-events-none absolute inset-[8px] rounded-full"
                    style={{
                      background: 'radial-gradient(46% 46% at 50% 50%, rgba(255,223,94,0.30) 0%, rgba(255,223,94,0.10) 36%, rgba(255,223,94,0) 65%)',
                      filter: 'blur(2px)',
                      mixBlendMode: 'screen'
                    }}
                  />
                  {/* 4) Specular highlight across top */}
                  <span
                    className="pointer-events-none absolute inset-0 rounded-full"
                    style={{
                      boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.12)'
                    }}
                  />
                  {/* 5) Label */}
                  <span
                    className="relative z-10"
                    style={{
                      color: '#FFE96A',
                      textShadow: '0 0 16px rgba(255,223,94,0.60), 0 0 36px rgba(255,223,94,0.28), 0 0 2px rgba(255,223,94,0.90)',
                      letterSpacing: '0.2px'
                    }}
                  >
                    Freeze PRD
                  </span>
                </button>
              </div>
              
              {/* PRD Content Preview */}
              {status !== 'ready' ? (
                <div className="space-y-3" aria-label="PRD preview placeholder">
                  {/* Problem placeholder */}
                  <div className="flex items-start gap-3">
                    <span style={{ color: 'var(--text-strong)', minWidth: 'fit-content' }}>• Problem.</span>
                    <div className="space-y-1 flex-1">
                      <div className="h-3 w-4/5 rounded bg-white/5 animate-pulse" />
                      <div className="h-3 w-3/5 rounded bg-white/5 animate-pulse" />
                    </div>
                  </div>
                  
                  {/* Audience placeholder */}
                  <div className="flex items-center gap-3">
                    <span style={{ color: 'var(--text-strong)', minWidth: 'fit-content' }}>• Audience.</span>
                    <div className="h-3 w-2/3 rounded bg-white/5 animate-pulse" />
                  </div>
                  
                  {/* Goals placeholder */}
                  <div className="flex items-start gap-3">
                    <span style={{ color: 'var(--text-strong)', minWidth: 'fit-content' }}>• Goals.</span>
                    <div className="space-y-1 flex-1">
                      <div className="h-3 w-3/4 rounded bg-white/5 animate-pulse" />
                      <div className="h-3 w-4/5 rounded bg-white/5 animate-pulse" />
                      <div className="h-3 w-2/3 rounded bg-white/5 animate-pulse" />
                    </div>
                  </div>
                  
                  {/* Risks placeholder */}
                  <div className="flex items-center gap-3">
                    <span style={{ color: 'var(--text-strong)', minWidth: 'fit-content' }}>• Risks.</span>
                    <div className="h-3 w-1/2 rounded bg-white/5 animate-pulse" />
                  </div>
                  
                  {/* Competitive scan placeholder */}
                  <div className="flex items-start gap-3">
                    <span style={{ color: 'var(--text-strong)', minWidth: 'fit-content' }}>• Competitive scan.</span>
                    <div className="space-y-1 flex-1">
                      <div className="h-3 w-3/5 rounded bg-white/5 animate-pulse" />
                      <div className="h-3 w-4/5 rounded bg-white/5 animate-pulse" />
                    </div>
                  </div>
                  
                  {/* Open questions placeholder */}
                  <div className="flex items-start gap-3">
                    <span style={{ color: 'var(--text-strong)', minWidth: 'fit-content' }}>• Open questions.</span>
                    <div className="space-y-1 flex-1">
                      <div className="h-3 w-4/5 rounded bg-white/5 animate-pulse" />
                      <div className="h-3 w-3/4 rounded bg-white/5 animate-pulse" />
                      <div className="h-3 w-2/3 rounded bg-white/5 animate-pulse" />
                    </div>
                  </div>
                </div>
              ) : (
                <PRDSummaryDisplay 
                  prdContent={prdContent}
                  sessionId={sessionId}
                />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Link Modal */}
      <AnimatePresence>
        {showLinkModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
            onClick={() => setShowLinkModal(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-gray-900 rounded-2xl p-6 w-96 max-w-[90vw]"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--text-strong)' }}>
                Paste Link
              </h3>
              <input
                type="url"
                value={linkUrl}
                onChange={(e) => setLinkUrl(e.target.value)}
                placeholder="https://..."
                className="w-full px-4 py-3 rounded-lg bg-gray-800 border border-gray-700 text-white placeholder-gray-400 focus:outline-none focus:border-blue-500"
                autoFocus
              />
              <div className="flex gap-3 mt-4">
                <button
                  onClick={() => setShowLinkModal(false)}
                  className="flex-1 py-2 px-4 rounded-lg border border-gray-600 text-gray-300 hover:bg-gray-800"
                >
                  Cancel
                </button>
                <button
                  onClick={handleLinkSubmit}
                  disabled={!linkUrl.trim()}
                  className="flex-1 py-2 px-4 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Add Link
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}