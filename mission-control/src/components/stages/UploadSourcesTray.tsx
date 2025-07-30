/**
 * UploadSourcesTray - Upload Sources tray component for Think Stage
 * 
 * This component implements the Upload Sources tray interface shown in the mockup:
 * - Dashed drop zone with drag-and-drop functionality
 * - "Upload" and "Paste link" buttons
 * - File chips with progress indicators
 * - 4-dot progress line (Reading files → Pulling key points → Drafting PRD → Ready to review)
 * - PRD preview with source attribution
 * 
 * Requirements addressed:
 * - Requirement 1.1-1.6: Upload Sources Tray Interface
 * - Requirement 4.1-4.2: Progress Tracking and PRD Preview
 */

import React, { useState, useCallback, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { LiquidCard } from '@/components/core/LiquidCard'
import { FileChip } from './FileChip'
import { ProgressLine } from './ProgressLine'
import { PRDPreview } from './PRDPreview'
import { missionControlApi } from '@/services/api/missionControlApi'

interface UploadedFile {
  id: string
  name: string
  type: 'pdf' | 'jpg' | 'png' | 'gif' | 'url'
  size?: number
  url?: string
  status: 'uploading' | 'processing' | 'complete' | 'error'
  progress: number
  sourceId?: string // S1, S2, etc.
}

interface UploadSourcesTrayProps {
  projectId: string
  onUploadComplete?: (sessionId: string) => void
  className?: string
}

type ProcessingStage = 'idle' | 'reading' | 'extracting' | 'drafting' | 'ready'

export const UploadSourcesTray: React.FC<UploadSourcesTrayProps> = ({
  projectId,
  onUploadComplete,
  className,
}) => {
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [isDragOver, setIsDragOver] = useState(false)
  const [showLinkModal, setShowLinkModal] = useState(false)
  const [processingStage, setProcessingStage] = useState<ProcessingStage>('idle')
  const [prdContent, setPrdContent] = useState<string>('')
  const [showPRDPreview, setShowPRDPreview] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const dropZoneRef = useRef<HTMLDivElement>(null)
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

  // Handle file drop
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    
    const droppedFiles = Array.from(e.dataTransfer.files)
    handleFiles(droppedFiles)
  }, [])

  // Handle file selection
  const handleFiles = useCallback(async (fileList: File[]) => {
    if (!sessionId) {
      setError('Upload session not ready')
      return
    }

    setIsUploading(true)
    setError(null)

    try {
      // Filter supported files
      const supportedFiles = fileList.filter(file => {
        const fileType = getFileType(file.name, file.type)
        return fileType !== null
      })

      if (supportedFiles.length === 0) {
        setError('No supported files found. Please upload PDF, JPG, PNG, or GIF files.')
        setIsUploading(false)
        return
      }

      // Add files to UI immediately with uploading status
      const newFiles: UploadedFile[] = supportedFiles.map((file, index) => {
        const fileType = getFileType(file.name, file.type)!
        return {
          id: `file-${Date.now()}-${index}`,
          name: file.name,
          type: fileType,
          size: file.size,
          status: 'uploading',
          progress: 0,
          sourceId: `S${files.length + index + 1}`,
        }
      })

      setFiles(prev => [...prev, ...newFiles])

      // Upload files to backend
      const uploadResult = await missionControlApi.uploadFiles(sessionId, supportedFiles)
      
      console.log('Upload result:', uploadResult)

      // Update file status based on upload result
      setFiles(prev => prev.map(file => {
        const uploadedFile = uploadResult.uploaded_files.find(uf => uf.filename === file.name)
        if (uploadedFile) {
          return {
            ...file,
            id: uploadedFile.id,
            status: 'processing',
            progress: 100,
            sourceId: uploadedFile.source_id
          }
        }
        return file
      }))

      // Start polling for file processing status
      startStatusPolling()

      if (uploadResult.errors && uploadResult.errors.length > 0) {
        setError(`Some files failed to upload: ${uploadResult.errors.join(', ')}`)
      }

    } catch (error) {
      console.error('File upload failed:', error)
      setError('Failed to upload files. Please try again.')
      
      // Mark files as error
      setFiles(prev => prev.map(file => 
        file.status === 'uploading' ? { ...file, status: 'error' } : file
      ))
    } finally {
      setIsUploading(false)
    }
  }, [sessionId, files.length])

  // Get file type from name and mime type
  const getFileType = (name: string, mimeType: string): UploadedFile['type'] | null => {
    const extension = name.split('.').pop()?.toLowerCase()
    
    if (extension === 'pdf' || mimeType === 'application/pdf') return 'pdf'
    if (['jpg', 'jpeg'].includes(extension!) || mimeType.startsWith('image/jpeg')) return 'jpg'
    if (extension === 'png' || mimeType === 'image/png') return 'png'
    if (extension === 'gif' || mimeType === 'image/gif') return 'gif'
    
    return null
  }

  // Start polling for file processing status
  const startStatusPolling = useCallback(() => {
    if (!sessionId || statusPollingRef.current) return

    statusPollingRef.current = setInterval(async () => {
      try {
        const status = await missionControlApi.getUploadStatus(sessionId)
        
        // Update file statuses
        setFiles(prev => prev.map(file => {
          const statusFile = status.files.find(sf => sf.id === file.id)
          if (statusFile) {
            return {
              ...file,
              status: statusFile.processing_status as UploadedFile['status'],
              progress: statusFile.processing_status === 'complete' ? 100 : 
                       statusFile.processing_status === 'processing' ? 75 : 
                       statusFile.processing_status === 'error' ? 0 : file.progress
            }
          }
          return file
        }))

        // Stop polling if all files are processed
        if (status.overall_status === 'complete' || status.overall_status === 'error') {
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

  // Handle drag events
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    if (!dropZoneRef.current?.contains(e.relatedTarget as Node)) {
      setIsDragOver(false)
    }
  }, [])

  // Handle file input click
  const handleUploadClick = () => {
    fileInputRef.current?.click()
  }

  // Handle file input change
  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFiles(Array.from(e.target.files))
    }
  }

  // Handle link paste
  const handleLinkPaste = useCallback(async (url: string) => {
    if (!sessionId) {
      setError('Upload session not ready')
      return
    }

    setIsUploading(true)
    setError(null)
    setShowLinkModal(false)

    try {
      // Add URL to UI immediately
      const newFile: UploadedFile = {
        id: `url-${Date.now()}`,
        name: new URL(url).hostname,
        type: 'url',
        url,
        status: 'uploading',
        progress: 0,
        sourceId: `S${files.length + 1}`,
      }
      
      setFiles(prev => [...prev, newFile])

      // Upload URL to backend
      const uploadResult = await missionControlApi.uploadLinks(sessionId, [url])
      
      console.log('Link upload result:', uploadResult)

      // Update file status
      setFiles(prev => prev.map(file => {
        if (file.id === newFile.id) {
          const uploadedLink = uploadResult.uploaded_links[0]
          return {
            ...file,
            id: uploadedLink.id,
            status: 'complete', // URLs are processed immediately
            progress: 100,
            sourceId: uploadedLink.source_id
          }
        }
        return file
      }))

      if (uploadResult.errors && uploadResult.errors.length > 0) {
        setError(`Link upload failed: ${uploadResult.errors.join(', ')}`)
      }

    } catch (error) {
      console.error('Link upload failed:', error)
      setError('Failed to upload link. Please try again.')
      
      // Mark link as error
      setFiles(prev => prev.map(file => 
        file.status === 'uploading' ? { ...file, status: 'error' } : file
      ))
    } finally {
      setIsUploading(false)
    }
  }, [sessionId, files.length])

  // Remove file
  const handleRemoveFile = (fileId: string) => {
    setFiles(prev => prev.filter(file => file.id !== fileId))
  }

  // Start PRD generation
  const handleMakePRDDraft = useCallback(async () => {
    if (!sessionId || files.length === 0) return
    
    setProcessingStage('reading')
    setError(null)

    try {
      // Start AI analysis
      const analysisResult = await missionControlApi.analyzeSessionFiles(sessionId, 'claude-opus-4')
      
      console.log('Analysis result:', analysisResult)

      if (analysisResult.status === 'success') {
        // Simulate processing stages for better UX
        const stages: ProcessingStage[] = ['reading', 'extracting', 'drafting', 'ready']
        let currentStageIndex = 0
        
        const interval = setInterval(() => {
          currentStageIndex++
          if (currentStageIndex < stages.length) {
            setProcessingStage(stages[currentStageIndex])
          } else {
            clearInterval(interval)
            
            // Get the full session context with AI analysis
            getSessionContext()
          }
        }, 1500) // Faster progression since real processing is happening

      } else {
        setError(analysisResult.error || 'AI analysis failed')
        setProcessingStage('idle')
      }

    } catch (error) {
      console.error('PRD generation failed:', error)
      setError('Failed to generate PRD. Please try again.')
      setProcessingStage('idle')
    }
  }, [sessionId, files.length])

  // Get session context with AI analysis
  const getSessionContext = useCallback(async () => {
    if (!sessionId) return

    try {
      const context = await missionControlApi.getSessionContext(sessionId)
      
      if (context.ai_analysis) {
        setPrdContent(context.ai_analysis)
        setShowPRDPreview(true)
        console.log('PRD generated successfully')
      } else {
        setError('No AI analysis available')
        setProcessingStage('idle')
      }

    } catch (error) {
      console.error('Failed to get session context:', error)
      setError('Failed to retrieve generated PRD')
      setProcessingStage('idle')
    }
  }, [sessionId])

  // Check if ready to process
  const canProcess = files.length > 0 && files.every(file => file.status === 'complete')

  return (
    <div className={clsx('space-y-6', className)}>
      {/* Sources Tray Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-white">Sources tray</h2>
        <div className="flex items-center space-x-2">
          {sessionId && (
            <span className="text-xs text-green-400">Session: {sessionId.slice(0, 8)}...</span>
          )}
          <button className="text-green-400 hover:text-green-300 transition-colors">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-red-900/50 border border-red-500 rounded-lg p-3"
        >
          <div className="flex items-center space-x-2">
            <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-red-300 text-sm">{error}</span>
            <button 
              onClick={() => setError(null)}
              className="ml-auto text-red-400 hover:text-red-300"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </motion.div>
      )}

      {/* Upload Zone */}
      <LiquidCard
        variant="default"
        className="min-h-[200px] relative"
        interactive={false}
      >
        <div
          ref={dropZoneRef}
          className={clsx(
            'h-full border-2 border-dashed rounded-lg transition-all duration-300',
            'flex flex-col items-center justify-center space-y-4',
            isDragOver 
              ? 'border-green-400 bg-green-400/10' 
              : 'border-gray-600 hover:border-gray-500'
          )}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
        >
          <div className="text-center space-y-2">
            <p className="text-gray-400 text-sm">
              Drop PDFs, decks, Zoom links, webpages, Figma, screenshots
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center space-x-4">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={handleUploadClick}
              disabled={isUploading || !sessionId}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
            >
              {isUploading ? 'Uploading...' : 'Upload'}
            </motion.button>
            
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setShowLinkModal(true)}
              disabled={isUploading || !sessionId}
              className="px-6 py-2 bg-gray-700 hover:bg-gray-600 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
            >
              Paste link
            </motion.button>
          </div>
        </div>

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.jpg,.jpeg,.png,.gif"
          onChange={handleFileInputChange}
          className="hidden"
        />
      </LiquidCard>

      {/* File Chips */}
      {files.length > 0 && (
        <div className="space-y-3">
          <AnimatePresence>
            {files.map((file) => (
              <motion.div
                key={file.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
              >
                <FileChip
                  file={file}
                  onRemove={() => handleRemoveFile(file.id)}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Progress Line */}
      {processingStage !== 'idle' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <ProgressLine currentStage={processingStage} />
        </motion.div>
      )}

      {/* Make PRD Draft Button */}
      {canProcess && processingStage === 'idle' && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="flex justify-center"
        >
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleMakePRDDraft}
            disabled={!sessionId}
            className="px-8 py-3 bg-green-600 hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg font-medium transition-colors"
          >
            Make PRD draft
          </motion.button>
        </motion.div>
      )}

      {/* PRD Preview */}
      {showPRDPreview && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <PRDPreview
            content={prdContent}
            files={files}
            onFreezePRD={() => {
              // Handle freeze PRD action
              if (sessionId) {
                onUploadComplete?.(sessionId)
              }
            }}
          />
        </motion.div>
      )}

      {/* Link Modal */}
      <AnimatePresence>
        {showLinkModal && (
          <LinkPasteModal
            onSubmit={handleLinkPaste}
            onClose={() => setShowLinkModal(false)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

// Link Paste Modal Component
interface LinkPasteModalProps {
  onSubmit: (url: string) => void
  onClose: () => void
}

const LinkPasteModal: React.FC<LinkPasteModalProps> = ({ onSubmit, onClose }) => {
  const [url, setUrl] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (url.trim()) {
      onSubmit(url.trim())
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="bg-gray-800 rounded-lg p-6 w-full max-w-md mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold text-white mb-4">Paste Link</h3>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://..."
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            autoFocus
          />
          
          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!url.trim()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
            >
              Add Link
            </button>
          </div>
        </form>
      </motion.div>
    </motion.div>
  )
}

export default UploadSourcesTray