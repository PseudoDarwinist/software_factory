/**
 * SourcesTrayCard - Pixel-perfect futuristic glass UI component
 * Matches the exact specification for the Think → Refinery screen
 */

import React, { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

// Types
interface FileItem {
  name: string
  type: 'pdf' | 'video' | 'image' | 'document' | 'link'
  progress: number // 0-1
  error?: string
}

interface SourcesTrayCardProps {
  status: 'idle' | 'uploading' | 'analyzing' | 'drafting' | 'ready'
  files: FileItem[]
  onFileAdd?: (files: File[]) => void
  onLinkAdd?: (url: string) => void
  onFileRemove?: (index: number) => void
  onAnalyze?: () => void
  onFreezePRD?: () => void
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

export const SourcesTrayCard: React.FC<SourcesTrayCardProps> = ({
  status = 'idle',
  files = [],
  onFileAdd,
  onLinkAdd,
  onFileRemove,
  onAnalyze,
  onFreezePRD
}) => {
  const [isDragOver, setIsDragOver] = useState(false)
  const [showLinkModal, setShowLinkModal] = useState(false)
  const [linkUrl, setLinkUrl] = useState('')

  // Progress steps
  const progressSteps = [
    { key: 'reading', label: 'Reading files', active: ['uploading', 'analyzing', 'drafting', 'ready'].includes(status) },
    { key: 'pulling', label: 'Pulling key points', active: ['analyzing', 'drafting', 'ready'].includes(status) },
    { key: 'drafting', label: 'Drafting PRD', active: ['drafting', 'ready'].includes(status) },
    { key: 'ready', label: 'Ready to review', active: ['ready'].includes(status) }
  ]

  // Drag and drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    const droppedFiles = Array.from(e.dataTransfer.files)
    onFileAdd?.(droppedFiles)
  }, [onFileAdd])

  // File input handler
  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || [])
    onFileAdd?.(selectedFiles)
  }, [onFileAdd])

  // Link submission
  const handleLinkSubmit = useCallback(() => {
    if (linkUrl.trim()) {
      onLinkAdd?.(linkUrl.trim())
      setLinkUrl('')
      setShowLinkModal(false)
    }
  }, [linkUrl, onLinkAdd])

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
              <h2 
                className="text-lg font-semibold tracking-wide"
                style={{ 
                  color: 'var(--text-strong)',
                  letterSpacing: '0.2px'
                }}
              >
                Sources tray
              </h2>
              
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
              >
                <PlusIcon />
              </button>
            </div>

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
                  onClick={onAnalyze}
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
                  onClick={() => { if (status === 'ready') onFreezePRD?.(); }}
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
                  <div className="flex items-center gap-3">
                    <span style={{ color: 'var(--text-strong)' }}>• Problem.</span>
                    <div className="h-3 w-3/5 rounded bg-white/5 animate-pulse" />
                  </div>
                  <div className="flex items-center gap-3">
                    <span style={{ color: 'var(--text-strong)' }}>• Goals.</span>
                    <div className="h-3 w-2/3 rounded bg-white/5 animate-pulse" />
                  </div>
                  <div className="flex items-center gap-3">
                    <span style={{ color: 'var(--text-strong)' }}>• Risks.</span>
                    <div className="h-3 w-1/2 rounded bg-white/5 animate-pulse" />
                  </div>
                </div>
              ) : (
                <div className="space-y-2" aria-label="PRD preview">
                  {/* TODO: render real PRD bullets with source tags here */}
                </div>
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