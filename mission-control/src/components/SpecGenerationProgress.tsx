/**
 * SpecGenerationProgress - Real-time progress indicator for async spec generation
 * 
 * Shows progress bar, current stage, and provides cancel functionality
 * Connects to WebSocket for real-time updates
 */

import React, { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { io, Socket } from 'socket.io-client'
import { missionControlApi } from '@/services/api/missionControlApi'

interface SpecGenerationProgressProps {
  itemId: string
  jobId: number
  provider: string
  onComplete: (specId: string) => void
  onError: (error: string) => void
  onCancel: () => void
  className?: string
}

interface JobStatus {
  job_id: number
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  created_at: string | null
  started_at: string | null
  completed_at: string | null
  error_message: string | null
  metadata: any
  estimated_completion?: number
}

interface ProgressEvent {
  job_id: number
  item_id: string
  progress: number
  stage: string
  message: string
  timestamp: string
}

interface CompleteEvent {
  job_id: number
  item_id: string
  spec_id: string
  artifacts_created: string[]
  processing_time: number
  provider: string
  timestamp: string
}

interface FailedEvent {
  job_id: number
  item_id: string
  error: string
  provider: string
  retry_available: boolean
  timestamp: string
}

const STAGE_LABELS: Record<string, string> = {
  'initializing': 'Initializing...',
  'creating_event': 'Preparing request...',
  'initializing_agent': 'Starting AI agent...',
  'processing': 'Analyzing and generating...',
  'generating_requirements': 'Creating requirements...',
  'generating_design': 'Creating design...',
  'generating_tasks': 'Creating tasks...',
  'finalizing': 'Finalizing specification...',
  'completed': 'Completed!'
}

export const SpecGenerationProgress: React.FC<SpecGenerationProgressProps> = ({
  itemId,
  jobId,
  provider,
  onComplete,
  onError,
  onCancel,
  className
}) => {
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null)
  const [currentStage, setCurrentStage] = useState<string>('initializing')
  const [currentMessage, setCurrentMessage] = useState<string>('Starting spec generation...')
  const [socket, setSocket] = useState<Socket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isCancelling, setIsCancelling] = useState(false)

  // Fetch initial job status
  const fetchJobStatus = useCallback(async () => {
    try {
      const status = await missionControlApi.getJobStatus(jobId)
      // Cast the status to our expected type
      const typedStatus: JobStatus = {
        ...status,
        status: status.status as JobStatus['status']
      }
      setJobStatus(typedStatus)
      
      if (status.status === 'completed') {
        onComplete(status.metadata?.spec_id || `spec_${itemId}`)
      } else if (status.status === 'failed') {
        onError(status.error_message || 'Spec generation failed')
      } else if (status.status === 'cancelled') {
        onCancel()
      }
    } catch (error) {
      console.error('Failed to fetch job status:', error)
      onError('Failed to get generation status')
    }
  }, [jobId, itemId, onComplete, onError, onCancel])

  // Initialize WebSocket connection
  useEffect(() => {
    const socketUrl = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
    const newSocket = io(socketUrl, { 
      transports: ['websocket'],
      autoConnect: true
    })
    
    setSocket(newSocket)

    newSocket.on('connect', () => {
      console.log('WebSocket connected for spec generation progress')
      setIsConnected(true)
    })

    newSocket.on('disconnect', () => {
      console.log('WebSocket disconnected')
      setIsConnected(false)
    })

    // Listen for progress events
    newSocket.on('spec.generation.progress', (data: ProgressEvent) => {
      if (data.job_id === jobId && data.item_id === itemId) {
        setJobStatus(prev => prev ? { ...prev, progress: data.progress } : null)
        setCurrentStage(data.stage)
        setCurrentMessage(data.message)
      }
    })

    // Listen for completion events
    newSocket.on('spec.generation.complete', (data: CompleteEvent) => {
      if (data.job_id === jobId && data.item_id === itemId) {
        setJobStatus(prev => prev ? { ...prev, status: 'completed', progress: 100 } : null)
        setCurrentStage('completed')
        setCurrentMessage('Specification generated successfully!')
        onComplete(data.spec_id)
      }
    })

    // Listen for failure events
    newSocket.on('spec.generation.failed', (data: FailedEvent) => {
      if (data.job_id === jobId && data.item_id === itemId) {
        setJobStatus(prev => prev ? { ...prev, status: 'failed', error_message: data.error } : null)
        onError(data.error)
      }
    })

    // Listen for cancellation events
    newSocket.on('spec.generation.cancelled', (data: { job_id: number; item_id: string }) => {
      if (data.job_id === jobId && data.item_id === itemId) {
        setJobStatus(prev => prev ? { ...prev, status: 'cancelled' } : null)
        onCancel()
      }
    })

    return () => {
      newSocket.disconnect()
    }
  }, [jobId, itemId, onComplete, onError, onCancel])

  // Fetch initial status
  useEffect(() => {
    fetchJobStatus()
  }, [fetchJobStatus])

  // Handle cancel button click
  const handleCancel = async () => {
    if (isCancelling) return
    
    setIsCancelling(true)
    try {
      await missionControlApi.cancelJob(jobId)
      // The WebSocket event will handle the UI update
    } catch (error) {
      console.error('Failed to cancel job:', error)
      setIsCancelling(false)
    }
  }

  // Calculate estimated time remaining
  const getEstimatedTimeRemaining = (): string => {
    if (!jobStatus?.estimated_completion) return ''
    
    const remaining = Math.max(0, jobStatus.estimated_completion)
    if (remaining < 60) {
      return `~${Math.ceil(remaining)}s remaining`
    } else {
      return `~${Math.ceil(remaining / 60)}m remaining`
    }
  }

  // Get provider display name
  const getProviderDisplayName = (): string => {
    switch (provider) {
      case 'claude': return 'Claude Code'
      case 'model-garden': return 'AI Model Garden'
      default: return provider
    }
  }

  if (!jobStatus) {
    return (
      <div className={clsx('flex items-center space-x-2', className)}>
        <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm text-white/70">Loading...</span>
      </div>
    )
  }

  const progress = jobStatus.progress || 0
  const stageLabel = STAGE_LABELS[currentStage] || currentStage

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className={clsx('space-y-2', className)}
    >
      {/* Provider and status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium text-blue-400">
            🤖 {getProviderDisplayName()}
          </span>
          {jobStatus.status === 'running' && (
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
              <span className="text-xs text-white/60">Generating specs...</span>
            </div>
          )}
          {!isConnected && (
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-yellow-500 rounded-full" />
              <span className="text-xs text-yellow-400">Reconnecting...</span>
            </div>
          )}
        </div>
        
        {jobStatus.status === 'running' && (
          <button
            onClick={handleCancel}
            disabled={isCancelling}
            className="text-xs text-white/60 hover:text-white transition-colors disabled:opacity-50"
          >
            {isCancelling ? 'Cancelling...' : 'Cancel'}
          </button>
        )}
      </div>

      {/* Progress bar */}
      <div className="relative">
        <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-blue-500 to-purple-500 rounded-full"
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        </div>
        
        {/* Progress percentage */}
        <div className="absolute -top-1 right-0 text-xs text-white/60">
          {Math.round(progress)}%
        </div>
      </div>

      {/* Current stage and message */}
      <div className="space-y-1">
        <div className="text-sm text-white/80">{stageLabel}</div>
        <div className="text-xs text-white/60">{currentMessage}</div>
      </div>

      {/* Time estimate */}
      {jobStatus.status === 'running' && (
        <div className="text-xs text-white/50">
          ⏱️ {getEstimatedTimeRemaining()}
        </div>
      )}

      {/* Error state */}
      {jobStatus.status === 'failed' && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="p-2 bg-red-500/10 border border-red-500/20 rounded text-sm text-red-400"
        >
          ❌ Generation failed: {jobStatus.error_message}
        </motion.div>
      )}

      {/* Cancelled state */}
      {jobStatus.status === 'cancelled' && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="p-2 bg-yellow-500/10 border border-yellow-500/20 rounded text-sm text-yellow-400"
        >
          ⚠️ Generation cancelled
        </motion.div>
      )}
    </motion.div>
  )
}