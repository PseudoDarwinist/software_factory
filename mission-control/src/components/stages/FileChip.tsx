/**
 * FileChip - Visual file representation component
 * 
 * This component implements the file chip design shown in the mockup:
 * - File name, type icon, and remove button
 * - Mini progress bar during processing
 * - Different states (uploading, processing, complete, error)
 * - File type icons (PDF, JPG, PNG, GIF, URL)
 * 
 * Requirements addressed:
 * - Requirement 1.5: File chips showing name, type icon, and remove button
 * - Requirement 1.6: Mini progress bar within each chip during processing
 */

import React from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'

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

interface FileChipProps {
  file: UploadedFile
  onRemove: () => void
  className?: string
}

export const FileChip: React.FC<FileChipProps> = ({
  file,
  onRemove,
  className,
}) => {
  // Get file type icon
  const getFileIcon = () => {
    switch (file.type) {
      case 'pdf':
        return (
          <svg className="w-4 h-4 text-red-400" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z" clipRule="evenodd" />
          </svg>
        )
      case 'jpg':
      case 'png':
      case 'gif':
        return (
          <svg className="w-4 h-4 text-green-400" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
          </svg>
        )
      case 'url':
        return (
          <svg className="w-4 h-4 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5zm-5 5a2 2 0 012.828 0 1 1 0 101.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 10-1.414-1.414l-1.5 1.5a2 2 0 11-2.828-2.828l3-3z" clipRule="evenodd" />
          </svg>
        )
      default:
        return (
          <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
          </svg>
        )
    }
  }

  // Get status color
  const getStatusColor = () => {
    switch (file.status) {
      case 'uploading':
        return 'border-blue-500 bg-blue-500/10'
      case 'processing':
        return 'border-yellow-500 bg-yellow-500/10'
      case 'complete':
        return 'border-green-500 bg-green-500/10'
      case 'error':
        return 'border-red-500 bg-red-500/10'
      default:
        return 'border-gray-600 bg-gray-600/10'
    }
  }

  // Get status text
  const getStatusText = () => {
    switch (file.status) {
      case 'uploading':
        return 'Uploading...'
      case 'processing':
        return 'Processing...'
      case 'complete':
        return 'Complete'
      case 'error':
        return 'Error'
      default:
        return ''
    }
  }

  // Format file size
  const formatFileSize = (bytes?: number) => {
    if (!bytes) return ''
    
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(1024))
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`
  }

  return (
    <motion.div
      layout
      className={clsx(
        'relative overflow-hidden rounded-lg border transition-all duration-300',
        getStatusColor(),
        className
      )}
    >
      {/* Progress bar background */}
      {(file.status === 'uploading' || file.status === 'processing') && (
        <motion.div
          className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent"
          initial={{ x: '-100%' }}
          animate={{ x: `${file.progress - 100}%` }}
          transition={{ duration: 0.3 }}
        />
      )}

      <div className="relative p-3 flex items-center space-x-3">
        {/* File icon */}
        <div className="flex-shrink-0">
          {getFileIcon()}
        </div>

        {/* File info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2">
            <p className="text-sm font-medium text-white truncate">
              {file.name}
            </p>
            {file.sourceId && (
              <span className="text-xs text-blue-400 bg-blue-400/20 px-2 py-1 rounded">
                {file.sourceId}
              </span>
            )}
          </div>
          
          <div className="flex items-center space-x-2 mt-1">
            <p className="text-xs text-gray-400 uppercase">
              {file.type}
            </p>
            {file.size && (
              <>
                <span className="text-xs text-gray-500">•</span>
                <p className="text-xs text-gray-400">
                  {formatFileSize(file.size)}
                </p>
              </>
            )}
            {file.status !== 'complete' && (
              <>
                <span className="text-xs text-gray-500">•</span>
                <p className="text-xs text-gray-400">
                  {getStatusText()}
                </p>
              </>
            )}
          </div>
        </div>

        {/* Progress indicator */}
        {(file.status === 'uploading' || file.status === 'processing') && (
          <div className="flex-shrink-0 w-8 h-8 relative">
            <svg className="w-8 h-8 transform -rotate-90" viewBox="0 0 32 32">
              <circle
                cx="16"
                cy="16"
                r="12"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                className="text-gray-600"
              />
              <motion.circle
                cx="16"
                cy="16"
                r="12"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                className="text-blue-400"
                strokeDasharray={`${2 * Math.PI * 12}`}
                initial={{ strokeDashoffset: 2 * Math.PI * 12 }}
                animate={{ 
                  strokeDashoffset: 2 * Math.PI * 12 * (1 - file.progress / 100)
                }}
                transition={{ duration: 0.3 }}
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-xs text-white font-medium">
                {Math.round(file.progress)}
              </span>
            </div>
          </div>
        )}

        {/* Status icon for complete/error */}
        {file.status === 'complete' && (
          <div className="flex-shrink-0 w-5 h-5 text-green-400">
            <svg fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
          </div>
        )}

        {file.status === 'error' && (
          <div className="flex-shrink-0 w-5 h-5 text-red-400">
            <svg fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </div>
        )}

        {/* Remove button */}
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={onRemove}
          className="flex-shrink-0 w-6 h-6 text-gray-400 hover:text-red-400 transition-colors"
        >
          <svg fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </motion.button>
      </div>

      {/* Mini progress bar at bottom */}
      {(file.status === 'uploading' || file.status === 'processing') && (
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-gray-700">
          <motion.div
            className="h-full bg-blue-400"
            initial={{ width: '0%' }}
            animate={{ width: `${file.progress}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      )}
    </motion.div>
  )
}

export default FileChip