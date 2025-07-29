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

import React, { useState, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { LiquidCard } from '@/components/core/LiquidCard'
import { FileChip } from './FileChip'
import { ProgressLine } from './ProgressLine'
import { PRDPreview } from './PRDPreview'

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
  const fileInputRef = useRef<HTMLInputElement>(null)
  const dropZoneRef = useRef<HTMLDivElement>(null)

  // Handle file drop
  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    
    const droppedFiles = Array.from(e.dataTransfer.files)
    handleFiles(droppedFiles)
  }, [])

  // Handle file selection
  const handleFiles = useCallback((fileList: File[]) => {
    const newFiles: UploadedFile[] = fileList.map((file, index) => {
      const fileType = getFileType(file.name, file.type)
      if (!fileType) return null
      
      return {
        id: `file-${Date.now()}-${index}`,
        name: file.name,
        type: fileType,
        size: file.size,
        status: 'uploading',
        progress: 0,
        sourceId: `S${files.length + index + 1}`,
      }
    }).filter(Boolean) as UploadedFile[]

    setFiles(prev => [...prev, ...newFiles])
    
    // Simulate file upload progress
    newFiles.forEach(file => {
      simulateFileUpload(file.id)
    })
  }, [files.length])

  // Get file type from name and mime type
  const getFileType = (name: string, mimeType: string): UploadedFile['type'] | null => {
    const extension = name.split('.').pop()?.toLowerCase()
    
    if (extension === 'pdf' || mimeType === 'application/pdf') return 'pdf'
    if (['jpg', 'jpeg'].includes(extension!) || mimeType.startsWith('image/jpeg')) return 'jpg'
    if (extension === 'png' || mimeType === 'image/png') return 'png'
    if (extension === 'gif' || mimeType === 'image/gif') return 'gif'
    
    return null
  }

  // Simulate file upload progress
  const simulateFileUpload = (fileId: string) => {
    let progress = 0
    const interval = setInterval(() => {
      progress += Math.random() * 20
      
      if (progress >= 100) {
        progress = 100
        clearInterval(interval)
        
        setFiles(prev => prev.map(file => 
          file.id === fileId 
            ? { ...file, status: 'complete', progress: 100 }
            : file
        ))
      } else {
        setFiles(prev => prev.map(file => 
          file.id === fileId 
            ? { ...file, progress }
            : file
        ))
      }
    }, 200)
  }

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
  const handleLinkPaste = (url: string) => {
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
    setShowLinkModal(false)
    simulateFileUpload(newFile.id)
  }

  // Remove file
  const handleRemoveFile = (fileId: string) => {
    setFiles(prev => prev.filter(file => file.id !== fileId))
  }

  // Start PRD generation
  const handleMakePRDDraft = () => {
    if (files.length === 0) return
    
    setProcessingStage('reading')
    
    // Simulate processing stages
    const stages: ProcessingStage[] = ['reading', 'extracting', 'drafting', 'ready']
    let currentStageIndex = 0
    
    const interval = setInterval(() => {
      currentStageIndex++
      if (currentStageIndex < stages.length) {
        setProcessingStage(stages[currentStageIndex])
      } else {
        clearInterval(interval)
        // Generate mock PRD content
        setPrdContent(generateMockPRD())
        setShowPRDPreview(true)
      }
    }, 2000)
  }

  // Generate mock PRD content
  const generateMockPRD = (): string => {
    return `# PRD draft (live doc)

## Problem
Nimiritmce qartessad toue tsct re-linqui scre [S1]

## Goals
Rislis Tvice hrstern protscru [S5] [S1]

## Risks
Competitive scan [S3]`
  }

  // Check if ready to process
  const canProcess = files.length > 0 && files.every(file => file.status === 'complete')

  return (
    <div className={clsx('space-y-6', className)}>
      {/* Sources Tray Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold text-white">Sources tray</h2>
        <button className="text-green-400 hover:text-green-300 transition-colors">
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
        </button>
      </div>

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
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
            >
              Upload
            </motion.button>
            
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setShowLinkModal(true)}
              className="px-6 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
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
            className="px-8 py-3 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors"
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
              onUploadComplete?.('mock-session-id')
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