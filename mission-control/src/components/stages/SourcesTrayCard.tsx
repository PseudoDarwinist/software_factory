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
  section?: string // Add section context for different quotes per section
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
  
  console.log('🔍 Parsing PRD summary from AI response:', aiResponse.substring(0, 200) + '...')
  
  // First try to parse as JSON (for new structured responses)
  try {
    const jsonData = JSON.parse(aiResponse)
    if (jsonData.problem && jsonData.audience) {
      console.log('✅ Successfully parsed JSON structured response')
      
      // Clean up any template text or placeholder content for text sections
      const cleanTextSection = (section: any): { text: string; sources: string[] } => {
        let text = section.text || ''
        // Remove template patterns and clean up
        text = text.replace(/Extract.*?from.*?files.*?focusing.*?on/gi, '')
        text = text.replace(/Define.*?based.*?on.*?specifications/gi, '')
        text = text.replace(/\*\*.*?\*\*/g, '') // Remove markdown bold
        text = text.replace(/\\n/g, ' ') // Convert \n to spaces
        text = text.replace(/###?\s*/g, '') // Remove markdown headers
        text = text.replace(/^\s*-\s*/gm, '') // Remove leading dashes
        text = text.trim()
        
        return {
          text,
          sources: Array.isArray(section.sources) ? section.sources : ['S1']
        }
      }

      // Clean up any template text or placeholder content for list sections
      const cleanListSection = (section: any): { items: string[]; sources: string[] } => {
        let items = section.items || []
        // Clean up template patterns in list items
        items = items.map((item: string) => {
          return item
            .replace(/Extract.*?infer.*?using.*?framework/gi, '')
            .replace(/Define.*?focused.*?on.*?improvement/gi, '')
            .replace(/Identify.*?addressing.*?efficiency/gi, '')
            .replace(/Generate.*?question.*?based.*?on/gi, '')
            .replace(/\*\*.*?\*\*/g, '') // Remove markdown bold
            .replace(/\\n/g, ' ') // Convert \n to spaces
            .trim()
        }).filter((item: string) => item.length > 10) // Filter out very short items
        
        return {
          items,
          sources: Array.isArray(section.sources) ? section.sources : items.map(() => 'S1')
        }
      }
      
      return {
        problem: cleanTextSection(jsonData.problem),
        audience: cleanTextSection(jsonData.audience),
        goals: cleanListSection(jsonData.goals),
        risks: cleanListSection(jsonData.risks),
        competitive_scan: cleanListSection(jsonData.competitive_scan),
        open_questions: cleanListSection(jsonData.open_questions)
      }
    }
  } catch (e) {
    console.log('⚠️ Not JSON format, proceeding with text parsing')
  }
  
  // Enhanced text parsing for markdown-style responses
  const extractContent = (text: string) => {
    // More robust source tag extraction
    const sourceTags = text.match(/\bS\d+\b/g) || []
    const cleanText = text.replace(/\bS\d+\b/g, '').replace(/\s+/g, ' ').trim()
    return { text: cleanText, sources: [...new Set(sourceTags)] }
  }
  
  const extractListItems = (section: string, startMarkers = ['–', '-', '*', '•']) => {
    const items: string[] = []
    const sources: string[] = []
    
    const lines = section.split('\n')
    for (const line of lines) {
      const trimmed = line.trim()
      if (trimmed && startMarkers.some(marker => trimmed.startsWith(marker))) {
        const content = trimmed.replace(/^[–\-*•]\s*/, '').trim()
        if (content) {
          const { text, sources: lineSources } = extractContent(content)
          items.push(text)
          sources.push(lineSources[0] || 'S1')
        }
      }
    }
    
    return { items, sources }
  }
  
  // Split by major sections (bullet points or headers)
  const sections = aiResponse.split(/^[•▪]\s*/m).filter(s => s.trim())
  
  for (const section of sections) {
    const lines = section.trim().split('\n')
    const headerLine = lines[0]?.trim().toLowerCase()
    if (!headerLine) continue
    
    console.log('🔍 Processing section:', headerLine.substring(0, 50))
    
    if (headerLine.includes('problem')) {
      // Extract problem text (usually first line after header)
      let problemText = headerLine.replace(/^problem[.:]\s*/i, '').trim()
      if (!problemText && lines.length > 1) {
        problemText = lines[1]?.trim() || ''
      }
      const { text, sources } = extractContent(problemText)
      summary.problem.text = text
      summary.problem.sources = sources
      console.log('✅ Extracted problem:', text)
      
    } else if (headerLine.includes('audience')) {
      let audienceText = headerLine.replace(/^audience[.:]\s*/i, '').trim()
      if (!audienceText && lines.length > 1) {
        audienceText = lines[1]?.trim() || ''
      }
      const { text, sources } = extractContent(audienceText)
      summary.audience.text = text
      summary.audience.sources = sources
      console.log('✅ Extracted audience:', text)
      
    } else if (headerLine.includes('goal')) {
      const { items, sources } = extractListItems(section)
      if (items.length > 0) {
        summary.goals.items = items
        summary.goals.sources = sources
        console.log('✅ Extracted goals:', items.length, 'items')
      }
      
    } else if (headerLine.includes('risk')) {
      // Check if risks are in list format or single line
      const { items, sources } = extractListItems(section)
      if (items.length > 0) {
        summary.risks.items = items
        summary.risks.sources = sources
      } else {
        // Single risk in header line
        let riskText = headerLine.replace(/^risks?[.:]\s*/i, '').trim()
        if (riskText) {
          const { text, sources } = extractContent(riskText)
          summary.risks.items = [text]
          summary.risks.sources = sources
        }
      }
      console.log('✅ Extracted risks:', summary.risks.items.length, 'items')
      
    } else if (headerLine.includes('competitive')) {
      const { items, sources } = extractListItems(section)
      if (items.length > 0) {
        summary.competitive_scan.items = items
        summary.competitive_scan.sources = sources
        console.log('✅ Extracted competitive scan:', items.length, 'items')
      }
      
    } else if (headerLine.includes('question')) {
      const { items, sources } = extractListItems(section)
      if (items.length > 0) {
        summary.open_questions.items = items
        summary.open_questions.sources = sources
        console.log('✅ Extracted open questions:', items.length, 'items')
      }
    }
  }
  
  // Log final summary
  console.log('🔍 Final parsed summary:', {
    problem: !!summary.problem.text,
    audience: !!summary.audience.text,
    goals: summary.goals.items.length,
    risks: summary.risks.items.length,
    competitive_scan: summary.competitive_scan.items.length,
    open_questions: summary.open_questions.items.length
  })
  
  return summary
}

// Helper function to extract section-specific source quotes from actual session files
const extractSourceQuotes = async (sessionId: string | null, prdContent?: string): Promise<Record<string, SourceQuote>> => {
  if (!sessionId) return {}
  
  try {
    // Fetch session context to get file information
    const context = await missionControlApi.getSessionContext(sessionId)
    const sourceQuotes: Record<string, SourceQuote> = {}
    
    console.log('🔍 Extracting source quotes for', context.files?.length || 0, 'files')
    
    // Try to parse PRD content to get section-specific information
    let parsedPRD: any = null
    if (prdContent) {
      try {
        parsedPRD = JSON.parse(prdContent)
      } catch {
        // Ignore parsing errors, will use fallback
      }
    }
    
    // Map files to source IDs (S1, S2, S3, etc.)
    context.files?.forEach((file: any, index: number) => {
      const sourceId = `S${index + 1}`
      let quote = `Content from ${file.filename}`
      
      try {
        // Extract meaningful quotes based on file type and content
        if (file.file_type === 'url' && context.combined_content) {
          // For URL files, extract from combined content
          const urlContent = context.combined_content.split('\n\n').find((section: string) => 
            section.includes(file.filename) || section.includes('URL:')
          )
          if (urlContent) {
            const lines = urlContent.split('\n').filter((line: string) => 
              line.trim() && !line.startsWith('URL:') && !line.startsWith('File:')
            )
            if (lines.length > 0) {
              quote = lines[0].trim().substring(0, 120) + (lines[0].length > 120 ? '...' : '')
            }
          }
        }
        
        // Extract different quotes from the original document or AI analysis
        if (context.ai_analysis && quote === `Content from ${file.filename}`) {
          // Try to extract from the full PRD content first (which contains original source quotes)
          if (parsedPRD && parsedPRD.full_prd) {
            // Look for quotes in the full PRD that seem to be from the original document
            const fullPrdText = parsedPRD.full_prd.replace(/\\n/g, '\n')
            
            // Extract meaningful sentences that look like they came from the source
            const meaningfulSentences = fullPrdText
              .split(/[.!?]+/)
              .map((s: string) => s.trim())
              .filter((s: string) => 
                s.length > 30 && 
                s.length < 150 && 
                !s.includes('##') && 
                !s.includes('**') &&
                !s.toLowerCase().includes('framework') &&
                !s.toLowerCase().includes('analysis') &&
                !s.toLowerCase().includes('section')
              )
            
            if (meaningfulSentences.length > 0) {
              // Use the first meaningful sentence as the quote
              quote = meaningfulSentences[0] + '.'
              if (quote.length > 120) {
                quote = quote.substring(0, 120) + '...'
              }
            }
          }
          
          // Fallback to AI analysis if no PRD content
          if (quote === `Content from ${file.filename}`) {
            const keyInsights = [
              // Look for specific business insights
              /remote teams.*?(?:struggle|challenge|difficulty).*?with.*?([^.!?]{20,100})[.!?]/i,
              /(?:users|customers|teams).*?(?:need|require|want).*?([^.!?]{20,100})[.!?]/i,
              /(?:productivity|efficiency|collaboration).*?(?:improved?|enhanced?|increased?).*?([^.!?]{20,100})[.!?]/i,
              /(?:market|business|revenue).*?(?:opportunity|potential|growth).*?([^.!?]{20,100})[.!?]/i
            ]
            
            for (const pattern of keyInsights) {
              const match = context.ai_analysis.match(pattern)
              if (match) {
                quote = match[0].trim()
                if (quote.length > 120) {
                  quote = quote.substring(0, 120) + '...'
                }
                break
              }
            }
          }
        }
        
        // Enhanced quote extraction from PRD preview
        if (context.prd_preview && quote === `Content from ${file.filename}`) {
          const prdLines = context.prd_preview.split('\n').filter((line: string) => line.trim())
          const contentPatterns = [
            /• Problem\.\s*([^S•]+)/i,
            /• Audience\.\s*([^S•]+)/i,
            /– ([^S–•]+)/i,
            /• Goals\.\s*\n\s*– ([^S–•]+)/i
          ]
          
          for (const pattern of contentPatterns) {
            const match = context.prd_preview.match(pattern)
            if (match && match[1]) {
              quote = match[1].trim()
              if (quote.length > 120) {
                quote = quote.substring(0, 120) + '...'
              }
              break
            }
          }
        }
        
        // Clean up the quote
        quote = quote.replace(/\s+/g, ' ').trim()
        if (!quote.endsWith('.') && !quote.endsWith('...') && !quote.endsWith('!') && !quote.endsWith('?')) {
          if (quote.length < 120) {
            quote += '.'
          }
        }
        
        console.log(`📝 Source ${sourceId} (${file.filename}): "${quote.substring(0, 50)}..."`)
        
      } catch (extractError) {
        console.error(`Failed to extract quote for ${file.filename}:`, extractError)
        // Keep the default quote
      }
      
      sourceQuotes[sourceId] = {
        sourceId,
        quote,
        filename: file.filename
      }
    })
    
    console.log('✅ Extracted', Object.keys(sourceQuotes).length, 'source quotes')
    return sourceQuotes
    
  } catch (error) {
    console.error('Failed to fetch source quotes:', error)
    // Return fallback quotes
    return {
      'S1': {
        sourceId: 'S1',
        quote: 'Content from uploaded document',
        filename: 'Document'
      }
    }
  }
}

// PRD Version Badge Component
interface PRDVersionBadgeProps {
  sessionId: string | null
}

const PRDVersionBadge: React.FC<PRDVersionBadgeProps> = ({ sessionId }) => {
  const [versionInfo, setVersionInfo] = useState<{
    version: string
    status: 'draft' | 'frozen'
  } | null>(null)

  useEffect(() => {
    if (!sessionId) return

    const fetchVersionInfo = async () => {
      try {
        const context = await missionControlApi.getSessionContext(sessionId)
        if (context.prd_info) {
          setVersionInfo({
            version: context.prd_info.version,
            status: context.prd_info.status as 'draft' | 'frozen'
          })
        }
      } catch (error) {
        console.error('Failed to fetch PRD version info:', error)
      }
    }

    fetchVersionInfo()

    // Set up event listener for PRD updates
    const handlePRDUpdate = (event: CustomEvent) => {
      if (event.detail?.session_id === sessionId) {
        setVersionInfo({
          version: event.detail.version,
          status: event.detail.status
        })
      }
    }

    // Listen for custom PRD update events
    window.addEventListener('prd.updated', handlePRDUpdate as EventListener)

    // For now, we'll also poll for updates every 30 seconds as fallback
    const pollInterval = setInterval(fetchVersionInfo, 30000)

    return () => {
      clearInterval(pollInterval)
      window.removeEventListener('prd.updated', handlePRDUpdate as EventListener)
    }
  }, [sessionId])

  if (!versionInfo) {
    return null
  }

  const isDraft = versionInfo.status === 'draft'
  const badgeColor = isDraft ? '#FFE96A' : '#48E0D8'
  const badgeText = isDraft ? `${versionInfo.version} draft` : `${versionInfo.version} frozen`

  return (
    <span
      className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium"
      style={{
        background: `rgba(${isDraft ? '255, 233, 106' : '72, 224, 216'}, 0.15)`,
        color: badgeColor,
        border: `1px solid rgba(${isDraft ? '255, 233, 106' : '72, 224, 216'}, 0.3)`,
        textShadow: `0 0 8px rgba(${isDraft ? '255, 233, 106' : '72, 224, 216'}, 0.4)`
      }}
    >
      {badgeText}
    </span>
  )
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
      console.log('🔍 PRD Content received:', prdContent.substring(0, 200) + '...')
      const parsedSummary = parsePRDSummary(prdContent)
      console.log('🔍 Parsed PRD Summary:', parsedSummary)
      setSummary(parsedSummary)
      
      // Load source quotes with PRD content for better extraction
      extractSourceQuotes(sessionId, prdContent).then(setSourceQuotes)
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
    
    const quote = sourceQuotes[sourceTag]?.quote || `Content from ${sourceQuotes[sourceTag]?.filename || 'document'}`
    console.log(`🔍 Rendering source tag ${sourceTag}:`, quote.substring(0, 50) + '...')
    
    return (
      <span
        className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium cursor-help transition-all duration-200 hover:scale-105"
        style={{
          background: 'rgba(72, 224, 216, 0.15)',
          color: 'var(--source-tag)',
          border: '1px solid rgba(72, 224, 216, 0.3)'
        }}
        onMouseEnter={() => setHoveredSource(sourceTag)}
        onMouseLeave={() => setHoveredSource(null)}
        title={quote}
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
          {section.sources && section.sources.length > 0 && (
            <span className="ml-2">
              {section.sources.map((source, idx) => (
                <span key={idx}>{renderSourceTag(source)}</span>
              ))}
            </span>
          )}
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
              <div className="flex-1">
                <span style={{ color: 'var(--text-dim)' }}>{item}</span>
                {section.sources && section.sources[idx] && (
                  <span className="ml-2">{renderSourceTag(section.sources[idx])}</span>
                )}
              </div>
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
          className="fixed z-50 p-3 rounded-lg shadow-lg max-w-sm pointer-events-none"
          style={{
            background: 'rgba(12, 17, 25, 0.95)',
            border: '1px solid rgba(72, 224, 216, 0.3)',
            backdropFilter: 'blur(12px)',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)'
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

  // Load existing session state when resuming
  const loadExistingSessionState = async (sessionId: string) => {
    try {
      console.log('🔄 Loading existing session state for:', sessionId)
      
      // Get session context with files and PRD content
      const context = await missionControlApi.getSessionContext(sessionId)
      
      // Restore files list
      if (context.files && context.files.length > 0) {
        const restoredFiles: FileItem[] = context.files.map((file: any) => ({
          name: file.filename,
          type: file.file_type === 'url' ? 'link' : 
                ['pdf', 'jpg', 'jpeg', 'png', 'gif'].includes(file.file_type) ? file.file_type as FileItem['type'] :
                'document' as FileItem['type'],
          progress: file.processing_status === 'complete' ? 1 : 
                   file.processing_status === 'processing' ? 0.75 : 
                   file.processing_status === 'error' ? 0 : 1,
          error: file.processing_status === 'error' ? 'Processing failed' : undefined
        }))
        
        setFiles(restoredFiles)
        console.log('✅ Restored', restoredFiles.length, 'files')
      }
      
      // Restore PRD content and status
      if (context.ai_analysis || context.prd_preview) {
        const prdText = context.prd_preview || context.ai_analysis
        setPrdContent(prdText)
        setStatus('ready')
        console.log('✅ Restored PRD content and set status to ready')
      } else if (context.status === 'ready') {
        setStatus('ready')
      } else if (context.files && context.files.length > 0) {
        // Has files but no PRD yet
        setStatus('idle')
        console.log('✅ Restored files, status set to idle (ready to analyze)')
      }
      
      console.log('✅ Successfully loaded existing session state')
      
    } catch (error) {
      console.error('❌ Failed to load existing session state:', error)
      // Don't set error here, just continue with empty state
    }
  }

  // Initialize or resume session when component mounts
  useEffect(() => {
    const initializeSession = async () => {
      try {
        console.log('🔍 Checking for existing sessions for project:', projectId)
        
        // First, try to find existing session for this project with PRD content
        try {
          // Get project sessions to see if we have an existing one
          const existingSessions = await missionControlApi.getProjectSessions?.(projectId)
          
          if (existingSessions && existingSessions.length > 0) {
            // Find the most recent session with files or PRD content
            const activeSession = existingSessions
              .filter((s: any) => s.status === 'ready' || s.file_count > 0)
              .sort((a: any, b: any) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())[0]
            
            if (activeSession) {
              console.log('✅ Found existing session to resume:', activeSession.session_id)
              setSessionId(activeSession.session_id)
              
              // Load existing session state
              await loadExistingSessionState(activeSession.session_id)
              return
            }
          }
        } catch (error) {
          console.log('⚠️ Could not check existing sessions, will create new one')
        }
        
        // No existing session found, create new one
        console.log('🆕 Creating new upload session for project:', projectId)
        const session = await missionControlApi.createUploadSession(projectId, 'Upload sources for PRD generation')
        setSessionId(session.session_id)
        console.log('✅ Created new upload session:', session.session_id)
        
      } catch (error) {
        console.error('❌ Failed to initialize upload session:', error)
        setError('Failed to initialize upload session')
      }
    }

    initializeSession()

    // Cleanup polling on unmount
    return () => {
      if (statusPollingRef.current) {
        clearInterval(statusPollingRef.current)
      }
    }
  }, [projectId])

  // Set up WebSocket listener for PRD updates
  useEffect(() => {
    if (!sessionId) return

    // Listen for custom events dispatched by webhook handlers
    const handleCustomPRDUpdate = (event: CustomEvent) => {
      if (event.detail.session_id === sessionId) {
        console.log('🔄 PRD updated via webhook:', event.detail)
        // Trigger a refresh of the PRD content
        if (event.detail.version && event.detail.status) {
          // Update UI to reflect new version status
          console.log(`PRD updated to ${event.detail.version} (${event.detail.status})`)
        }
      }
    }

    window.addEventListener('prd.updated', handleCustomPRDUpdate as EventListener)
    
    return () => {
      window.removeEventListener('prd.updated', handleCustomPRDUpdate as EventListener)
    }
  }, [sessionId])

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

  // Handle file removal
  const handleFileRemove = useCallback(async (index: number) => {
    const fileToRemove = files[index]
    if (!fileToRemove || !sessionId) return

    try {
      // Get session context to find the file ID
      const context = await missionControlApi.getSessionContext(sessionId)
      const backendFile = context.files.find(f => f.filename === fileToRemove.name)
      
      if (backendFile) {
        // Delete from backend
        await missionControlApi.deleteUploadedFile(backendFile.id)
        console.log(`✅ Deleted file: ${fileToRemove.name}`)
      }

      // Remove from UI immediately
      setFiles(prev => prev.filter((_, i) => i !== index))
      
      // Call original callback if provided
      onFileRemove?.(index)

    } catch (error) {
      console.error('Failed to remove file:', error)
      setError(`Failed to remove ${fileToRemove.name}`)
    }
  }, [files, sessionId, onFileRemove])

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
        return ['pdf', 'jpg', 'jpeg', 'png', 'gif', 'md', 'txt', 'doc', 'docx'].includes(extension || '')
      })

      if (supportedFiles.length === 0) {
        setError('No supported files found. Please upload PDF, JPG, PNG, GIF, MD, TXT, DOC, or DOCX files.')
        setStatus('idle')
        return
      }

      // Add files to UI immediately with uploading status
      const newFiles: FileItem[] = supportedFiles.map((file) => {
        const extension = file.name.split('.').pop()?.toLowerCase()
        const fileType = extension === 'pdf' ? 'pdf' : 
                        ['jpg', 'jpeg', 'png', 'gif'].includes(extension || '') ? 'image' : 
                        ['md', 'txt', 'doc', 'docx'].includes(extension || '') ? 'document' : 'document'
        
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
            console.log('🔍 Fetching session context for:', sessionId)
            const context = await missionControlApi.getSessionContext(sessionId)
            console.log('✅ Session context received:', context)
            
            if (context.ai_analysis) {
              // Use the structured PRD preview if available, otherwise use raw AI analysis
              const prdText = context.prd_preview || context.ai_analysis
              console.log('📝 PRD text length:', prdText.length)
              console.log('📝 PRD preview available:', !!context.prd_preview)
              setPrdContent(prdText)
              setStatus('ready')
              console.log('PRD generated successfully')
              

            } else {
              console.error('❌ No AI analysis in context:', context)
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
  const handleFreezePRD = useCallback(async () => {
    if (status === 'ready' && sessionId) {
      try {
        // Get the current PRD ID from session context
        const context = await missionControlApi.getSessionContext(sessionId)
        const prdId = context.prd_info?.id
        
        if (!prdId) {
          setError('No PRD found to freeze')
          return
        }
        
        // Call freeze endpoint
        const response = await missionControlApi.freezePRD(prdId, 'mission-control-user')
        
        if (response.success) {
          console.log('✅ PRD frozen successfully:', response.frozen_prd)
          
          // Trigger real-time update event
          const updateEvent = new CustomEvent('prd.updated', {
            detail: {
              session_id: sessionId,
              version: response.frozen_prd.version,
              status: response.frozen_prd.status,
              created_by: response.frozen_prd.created_by
            }
          })
          window.dispatchEvent(updateEvent)
          
          // Call original callbacks
          onFreezePRD?.()
          onUploadComplete?.(sessionId)
        } else {
          setError('Failed to freeze PRD')
        }
      } catch (error) {
        console.error('Error freezing PRD:', error)
        setError('Failed to freeze PRD')
      }
    }
  }, [status, sessionId, onFreezePRD, onUploadComplete])

  // Handle open full PRD
  const handleOpenFullPRD = useCallback(async () => {
    if (status === 'ready' && sessionId) {
      try {
        console.log('🔗 Generating PRD deep link for session:', sessionId)
        
        // Generate JWT deep link
        const response = await missionControlApi.generatePRDDeepLink(sessionId)
        
        console.log('🔗 Deep link response:', response)
        
        if (response && response.deep_link_url) {
          console.log('✅ Opening PRD in new tab:', response.deep_link_url)
          // Open in new tab
          window.open(response.deep_link_url, '_blank')
        } else {
          console.error('❌ Invalid deep link response:', response)
          setError('Failed to generate PRD link - invalid response')
        }
      } catch (error) {
        console.error('❌ Error opening full PRD:', error)
        setError(`Failed to open full PRD: ${error instanceof Error ? error.message : 'Unknown error'}`)
      }
    } else {
      console.warn('⚠️ Cannot open PRD - status:', status, 'sessionId:', sessionId)
      if (status !== 'ready') {
        setError('PRD is not ready yet')
      } else {
        setError('No active session')
      }
    }
  }, [status, sessionId])

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
                accept=".pdf,.doc,.docx,.md,.txt,.jpg,.jpeg,.png,.gif"
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
                        onClick={() => handleFileRemove(index)}
                        title={`Remove ${file.name}`}
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
                {/* Base progress line */}
                <div 
                  className="absolute top-1/2 left-0 right-0 h-px -translate-y-1/2"
                  style={{ background: 'linear-gradient(90deg, rgba(255,255,255,0.18), rgba(255,255,255,0.04))' }}
                />
                
                {/* Animated progress line overlay */}
                <div 
                  className="absolute top-1/2 left-0 h-px -translate-y-1/2 transition-all duration-1000 ease-out"
                  style={{ 
                    background: 'linear-gradient(90deg, rgba(255,233,106,0.9) 0%, rgba(255,216,77,0.7) 50%, rgba(255,233,106,0.9) 100%)',
                    boxShadow: '0 0 12px rgba(255,233,106,0.6), 0 0 24px rgba(255,216,77,0.4)',
                    width: `${Math.max(0, Math.min(100, (progressSteps.filter(s => s.active).length - 1) * 33.33))}%`,
                    opacity: progressSteps.some(s => s.active) ? 1 : 0
                  }}
                />
                
                {/* Flowing light effects during analysis */}
                {status === 'analyzing' && (
                  <>
                    {/* Primary flowing light */}
                    <div 
                      className="absolute top-1/2 left-0 h-px -translate-y-1/2"
                      style={{ 
                        background: 'radial-gradient(ellipse 40px 6px, rgba(255,233,106,1) 0%, rgba(255,233,106,0) 100%)',
                        width: '80px',
                        height: '6px',
                        filter: 'blur(1px)',
                        animation: 'flowRight 3s ease-in-out infinite',
                        animationDelay: '0s'
                      }}
                    />
                    {/* Secondary flowing light */}
                    <div 
                      className="absolute top-1/2 left-0 h-px -translate-y-1/2"
                      style={{ 
                        background: 'radial-gradient(ellipse 30px 4px, rgba(255,216,77,0.8) 0%, rgba(255,216,77,0) 100%)',
                        width: '60px',
                        height: '4px',
                        filter: 'blur(0.5px)',
                        animation: 'flowRight 2.5s ease-in-out infinite',
                        animationDelay: '0.8s'
                      }}
                    />
                    {/* Tertiary flowing light */}
                    <div 
                      className="absolute top-1/2 left-0 h-px -translate-y-1/2"
                      style={{ 
                        background: 'radial-gradient(ellipse 25px 3px, rgba(255,233,106,0.6) 0%, rgba(255,233,106,0) 100%)',
                        width: '50px',
                        height: '3px',
                        filter: 'blur(0.3px)',
                        animation: 'flowRight 2.2s ease-in-out infinite',
                        animationDelay: '1.5s'
                      }}
                    />
                  </>
                )}
                
                {/* Progress nodes */}
                {progressSteps.map((step, index) => (
                  <div key={step.key} className="relative flex flex-col items-center z-10">
                    <div
                      className={`w-3 h-3 rounded-full transition-all duration-500 relative ${
                        step.active ? 'shadow-lg' : ''
                      }`}
                      style={{
                        background: step.active ? '#FFE96A' : 'var(--progress-idle)',
                        boxShadow: step.active ? 
                          '0 0 10px rgba(255,233,106,0.8), 0 0 18px rgba(255,216,77,0.4), 0 0 24px rgba(255,233,106,0.2)' : 
                          'none'
                      }}
                    >
                      {/* Pulsing ring for active step */}
                      {step.active && (
                        <div
                          className="absolute inset-0 rounded-full animate-ping"
                          style={{
                            background: 'transparent',
                            border: '1px solid rgba(255,233,106,0.6)',
                            transform: 'scale(1.5)'
                          }}
                        />
                      )}
                    </div>
                    <span 
                      className="text-xs mt-2 whitespace-nowrap transition-colors duration-300"
                      style={{ 
                        color: step.active ? '#FFE96A' : 'var(--text-dim)',
                        textShadow: step.active ? '0 0 8px rgba(255,233,106,0.4)' : 'none'
                      }}
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
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-3">
                    <h3 
                      className="text-base font-semibold"
                      style={{ color: 'var(--text-strong)' }}
                    >
                      PRD draft <span style={{ color: 'var(--text-dim)' }}>(live doc)</span>
                    </h3>
                    <PRDVersionBadge sessionId={sessionId} />
                  </div>
                </div>
                
                <div className="flex items-center gap-3">
                  {/* Open full PRD button */}
                  <button
                    className="group relative inline-flex items-center justify-center rounded-full font-semibold text-sm transition-all duration-200 hover:scale-[1.01] active:scale-[0.99] focus:outline-none"
                    style={{
                      background: 'transparent',
                      border: 'none',
                      minWidth: '160px',
                      height: '44px',
                      padding: '0 24px',
                      filter: 'saturate(1.02)'
                    }}
                    onClick={handleOpenFullPRD}
                    aria-disabled={status !== 'ready'}
                    title={status === 'ready' ? 'Open full PRD in new tab' : 'PRD not ready yet'}
                  >
                    {/* Gradient ring */}
                    <span
                      className="pointer-events-none absolute inset-0 rounded-full"
                      style={{
                        padding: '2px',
                        borderRadius: '9999px',
                        background: 'linear-gradient(90deg, rgba(72,224,216,0.92) 0%, rgba(21,241,204,0.78) 38%, rgba(160,255,223,0.70) 100%)',
                        WebkitMask: 'linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)',
                        WebkitMaskComposite: 'xor',
                        maskComposite: 'exclude',
                        boxShadow: '0 0 18px rgba(72,224,216,0.35), 0 0 24px rgba(21,241,204,0.25)'
                      } as React.CSSProperties}
                    />
                    {/* Edge vignette */}
                    <span
                      className="pointer-events-none absolute inset-[2px] rounded-full"
                      style={{
                        background: 'radial-gradient(120% 100% at 50% 50%, rgba(0,0,0,0) 60%, rgba(0,0,0,0.22) 100%)',
                        mixBlendMode: 'multiply'
                      }}
                    />
                    {/* Luminous core */}
                    <span
                      className="pointer-events-none absolute inset-[6px] rounded-full"
                      style={{
                        background: 'radial-gradient(46% 46% at 50% 50%, rgba(72,224,216,0.30) 0%, rgba(72,224,216,0.10) 36%, rgba(72,224,216,0) 65%)',
                        filter: 'blur(2px)',
                        mixBlendMode: 'screen'
                      }}
                    />
                    {/* Specular highlight */}
                    <span
                      className="pointer-events-none absolute inset-0 rounded-full"
                      style={{
                        boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.12)'
                      }}
                    />
                    {/* Label */}
                    <span
                      className="relative z-10"
                      style={{
                        color: '#48E0D8',
                        textShadow: '0 0 16px rgba(72,224,216,0.60), 0 0 36px rgba(72,224,216,0.28), 0 0 2px rgba(72,224,216,0.90)',
                        letterSpacing: '0.2px'
                      }}
                    >
                      Open full PRD
                    </span>
                  </button>

                  {/* Freeze PRD button */}
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