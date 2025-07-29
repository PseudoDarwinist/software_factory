/**
 * PRDPreview - PRD preview component with source attribution
 * 
 * This component implements the PRD preview shown in the mockup:
 * - Quick PRD preview with source tags [S1], [S2]
 * - Hover tooltips showing exact quotes from source material
 * - "Freeze PRD" button to finalize the document
 * - Live document indicator
 * 
 * Requirements addressed:
 * - Requirement 4.2: PRD preview with source tags and hover tooltips
 * - Requirement 8.1-8.6: Source Attribution and Traceability
 */

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { LiquidCard } from '@/components/core/LiquidCard'

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

interface PRDPreviewProps {
  content: string
  files: UploadedFile[]
  onFreezePRD: () => void
  className?: string
}

interface SourceTooltipProps {
  sourceId: string
  files: UploadedFile[]
  children: React.ReactNode
}

// Mock source quotes for demonstration
const mockSourceQuotes: Record<string, string> = {
  'S1': 'Nimiritmce qartessad toue tsct re-linqui scre - this represents the core problem statement identified in the uploaded document.',
  'S2': 'Additional context from second source document providing supporting evidence.',
  'S3': 'Competitive analysis data showing market positioning and differentiation opportunities.',
  'S5': 'Goals and success metrics derived from stakeholder interviews and user research.'
}

// Source Tooltip Component
const SourceTooltip: React.FC<SourceTooltipProps> = ({ sourceId, files, children }) => {
  const [isHovered, setIsHovered] = useState(false)
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 })

  const handleMouseEnter = (e: React.MouseEvent) => {
    setIsHovered(true)
    const rect = e.currentTarget.getBoundingClientRect()
    setTooltipPosition({
      x: rect.left + rect.width / 2,
      y: rect.top - 10
    })
  }

  const handleMouseLeave = () => {
    setIsHovered(false)
  }

  const sourceFile = files.find(file => file.sourceId === sourceId)
  const quote = mockSourceQuotes[sourceId] || 'Source quote not available'

  return (
    <>
      <span
        className="inline-flex items-center px-1.5 py-0.5 text-xs font-medium bg-blue-500/20 text-blue-400 rounded cursor-help hover:bg-blue-500/30 transition-colors"
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {children}
      </span>

      <AnimatePresence>
        {isHovered && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 10 }}
            transition={{ duration: 0.2 }}
            className="fixed z-50 max-w-sm p-3 bg-gray-800 border border-gray-600 rounded-lg shadow-xl"
            style={{
              left: tooltipPosition.x,
              top: tooltipPosition.y,
              transform: 'translateX(-50%) translateY(-100%)'
            }}
          >
            {/* Arrow */}
            <div className="absolute top-full left-1/2 transform -translate-x-1/2">
              <div className="w-2 h-2 bg-gray-800 border-r border-b border-gray-600 transform rotate-45" />
            </div>

            {/* Content */}
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <span className="text-xs font-medium text-blue-400">{sourceId}</span>
                {sourceFile && (
                  <span className="text-xs text-gray-400">
                    {sourceFile.name}
                  </span>
                )}
              </div>
              <p className="text-sm text-gray-300 leading-relaxed">
                "{quote}"
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}

export const PRDPreview: React.FC<PRDPreviewProps> = ({
  content,
  files,
  onFreezePRD,
  className,
}) => {
  // Parse content and add source tooltips
  const parseContentWithSources = (text: string) => {
    const parts = text.split(/(\[S\d+\])/g)
    
    return parts.map((part, index) => {
      const sourceMatch = part.match(/\[S(\d+)\]/)
      if (sourceMatch) {
        const sourceId = `S${sourceMatch[1]}`
        return (
          <SourceTooltip key={index} sourceId={sourceId} files={files}>
            {part}
          </SourceTooltip>
        )
      }
      return <span key={index}>{part}</span>
    })
  }

  // Parse markdown-like content
  const parseMarkdown = (text: string) => {
    const lines = text.split('\n')
    
    return lines.map((line, index) => {
      if (line.startsWith('# ')) {
        return (
          <h1 key={index} className="text-xl font-bold text-white mb-4 flex items-center space-x-2">
            <span>{line.substring(2)}</span>
            <span className="text-sm font-normal text-gray-400 bg-gray-700 px-2 py-1 rounded">
              (live doc)
            </span>
          </h1>
        )
      }
      
      if (line.startsWith('## ')) {
        return (
          <h2 key={index} className="text-lg font-semibold text-white mt-6 mb-3">
            {line.substring(3)}
          </h2>
        )
      }
      
      if (line.trim() === '') {
        return <div key={index} className="h-2" />
      }
      
      return (
        <p key={index} className="text-gray-300 mb-2 leading-relaxed">
          {parseContentWithSources(line)}
        </p>
      )
    })
  }

  return (
    <div className={clsx('space-y-6', className)}>
      {/* PRD Preview Card */}
      <LiquidCard
        variant="default"
        className="min-h-[300px]"
        interactive={false}
      >
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-gray-700 pb-4">
            <div className="flex items-center space-x-3">
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
              <span className="text-sm text-gray-400">PRD Draft</span>
            </div>
            
            <div className="flex items-center space-x-2 text-xs text-gray-500">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
              </svg>
              <span>Auto-updating</span>
            </div>
          </div>

          {/* Content */}
          <div className="prose prose-invert max-w-none">
            {parseMarkdown(content)}
          </div>

          {/* Source Summary */}
          <div className="border-t border-gray-700 pt-4">
            <h3 className="text-sm font-medium text-gray-400 mb-3">Sources Referenced</h3>
            <div className="flex flex-wrap gap-2">
              {files.filter(file => file.sourceId).map((file) => (
                <div
                  key={file.id}
                  className="flex items-center space-x-2 px-3 py-2 bg-gray-700/50 rounded-lg"
                >
                  <span className="text-xs font-medium text-blue-400">
                    {file.sourceId}
                  </span>
                  <span className="text-xs text-gray-300">
                    {file.name}
                  </span>
                  <span className="text-xs text-gray-500 uppercase">
                    {file.type}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </LiquidCard>

      {/* Action Buttons */}
      <div className="flex justify-center space-x-4">
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-medium transition-colors"
        >
          Edit Draft
        </motion.button>
        
        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={onFreezePRD}
          className="px-8 py-3 bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600 text-white rounded-lg font-medium transition-all shadow-lg shadow-yellow-500/25"
        >
          Freeze PRD
        </motion.button>
      </div>

      {/* Completeness Checklist */}
      <LiquidCard
        variant="default"
        className="bg-gray-800/50"
        interactive={false}
      >
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-white">Completeness Check</h3>
          
          <div className="space-y-3">
            <ChecklistItem
              label="Goals have numbers"
              checked={true}
              description="Measurable success metrics are defined"
            />
            <ChecklistItem
              label="Risks cover accessibility/privacy"
              checked={false}
              description="Accessibility and privacy considerations are addressed"
            />
            <ChecklistItem
              label="At least 2 competitors"
              checked={true}
              description="Competitive analysis includes multiple competitors"
            />
            <ChecklistItem
              label="User stories are actionable"
              checked={true}
              description="User stories have clear acceptance criteria"
            />
          </div>

          <div className="pt-4 border-t border-gray-700">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-400">Completeness Score</span>
              <span className="text-lg font-semibold text-green-400">75%</span>
            </div>
            <div className="mt-2 w-full bg-gray-700 rounded-full h-2">
              <motion.div
                className="bg-green-400 h-2 rounded-full"
                initial={{ width: '0%' }}
                animate={{ width: '75%' }}
                transition={{ duration: 1, delay: 0.5 }}
              />
            </div>
          </div>
        </div>
      </LiquidCard>
    </div>
  )
}

// Checklist Item Component
interface ChecklistItemProps {
  label: string
  checked: boolean
  description: string
}

const ChecklistItem: React.FC<ChecklistItemProps> = ({ label, checked, description }) => {
  return (
    <div className="flex items-start space-x-3">
      <div className={clsx(
        'flex-shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center mt-0.5',
        checked 
          ? 'bg-green-500 border-green-500' 
          : 'border-gray-600 bg-transparent'
      )}>
        {checked && (
          <motion.svg
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.2 }}
            className="w-3 h-3 text-white"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </motion.svg>
        )}
      </div>
      
      <div className="flex-1">
        <p className={clsx(
          'text-sm font-medium',
          checked ? 'text-white' : 'text-gray-400'
        )}>
          {label}
        </p>
        <p className="text-xs text-gray-500 mt-1">
          {description}
        </p>
      </div>
    </div>
  )
}

export default PRDPreview