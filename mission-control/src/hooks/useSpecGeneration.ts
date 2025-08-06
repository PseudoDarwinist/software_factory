/**
 * useSpecGeneration - Custom hook for managing async spec generation state
 * 
 * Handles multiple concurrent spec generations, WebSocket connections,
 * and provides a clean API for starting, monitoring, and canceling generations
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { io, Socket } from 'socket.io-client'
import { missionControlApi } from '@/services/api/missionControlApi'

export interface GenerationJob {
  jobId: number
  itemId: string
  provider: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress: number
  stage: string
  message: string
  startedAt: Date
  estimatedCompletion?: number
  error?: string
}

export interface SpecGenerationState {
  // Map of item_id to generation job
  generatingSpecs: Map<string, GenerationJob>
  // Global connection status
  isConnected: boolean
  // Error states
  errors: Map<string, { error: string; retryAvailable: boolean; failedAt: Date }>
  // Completed specs awaiting UI update
  completedSpecs: Map<string, { specId: string; completedAt: Date }>
}

export interface UseSpecGenerationReturn {
  // Current state
  generatingSpecs: Map<string, GenerationJob>
  isConnected: boolean
  errors: Map<string, { error: string; retryAvailable: boolean; failedAt: Date }>
  completedSpecs: Map<string, { specId: string; completedAt: Date }>
  
  // Actions
  startGeneration: (itemId: string, provider: string) => Promise<number>
  cancelGeneration: (itemId: string) => Promise<boolean>
  retryGeneration: (itemId: string, provider?: string) => Promise<number>
  clearError: (itemId: string) => void
  clearCompleted: (itemId: string) => void
  
  // Utilities
  isGenerating: (itemId: string) => boolean
  getGenerationStatus: (itemId: string) => GenerationJob | null
  hasError: (itemId: string) => boolean
  isCompleted: (itemId: string) => boolean
  getActiveGenerationsCount: () => number
}

export const useSpecGeneration = (projectId: string): UseSpecGenerationReturn => {
  const [state, setState] = useState<SpecGenerationState>({
    generatingSpecs: new Map(),
    isConnected: false,
    errors: new Map(),
    completedSpecs: new Map()
  })
  
  const socketRef = useRef<Socket | null>(null)
  const projectIdRef = useRef(projectId)
  
  // Update project ID ref when it changes
  useEffect(() => {
    projectIdRef.current = projectId
  }, [projectId])

  // Initialize WebSocket connection
  useEffect(() => {
    const socketUrl = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
    const socket = io(socketUrl, { 
      transports: ['websocket'],
      autoConnect: true
    })
    
    socketRef.current = socket

    socket.on('connect', () => {
      console.log('WebSocket connected for spec generation management')
      setState(prev => ({ ...prev, isConnected: true }))
    })

    socket.on('disconnect', () => {
      console.log('WebSocket disconnected')
      setState(prev => ({ ...prev, isConnected: false }))
    })

    // Listen for progress events
    socket.on('spec.generation.progress', (data: {
      job_id: number
      item_id: string
      progress: number
      stage: string
      message: string
      timestamp: string
    }) => {
      setState(prev => {
        const newGeneratingSpecs = new Map(prev.generatingSpecs)
        const existingJob = newGeneratingSpecs.get(data.item_id)
        
        if (existingJob && existingJob.jobId === data.job_id) {
          newGeneratingSpecs.set(data.item_id, {
            ...existingJob,
            progress: data.progress,
            stage: data.stage,
            message: data.message,
            status: 'running'
          })
        }
        
        return { ...prev, generatingSpecs: newGeneratingSpecs }
      })
    })

    // Listen for completion events
    socket.on('spec.generation.complete', (data: {
      job_id: number
      item_id: string
      spec_id: string
      artifacts_created?: string[]
      processing_time?: number
      provider: string
      timestamp: string
      generation_type?: string
      artifact_data?: any
    }) => {
      setState(prev => {
        const newGeneratingSpecs = new Map(prev.generatingSpecs)
        const newCompletedSpecs = new Map(prev.completedSpecs)
        const newErrors = new Map(prev.errors)
        
        // Remove from generating
        newGeneratingSpecs.delete(data.item_id)
        
        // Add to completed
        newCompletedSpecs.set(data.item_id, {
          specId: data.spec_id,
          completedAt: new Date()
        })
        
        // Clear any previous errors
        newErrors.delete(data.item_id)
        
        return {
          ...prev,
          generatingSpecs: newGeneratingSpecs,
          completedSpecs: newCompletedSpecs,
          errors: newErrors
        }
      })
    })

    // Listen for failure events
    socket.on('spec.generation.failed', (data: {
      job_id: number
      item_id: string
      error: string
      provider: string
      retry_available: boolean
      timestamp: string
      generation_type?: string
    }) => {
      setState(prev => {
        const newGeneratingSpecs = new Map(prev.generatingSpecs)
        const newErrors = new Map(prev.errors)
        
        // Remove from generating
        newGeneratingSpecs.delete(data.item_id)
        
        // Add to errors
        newErrors.set(data.item_id, {
          error: data.error,
          retryAvailable: data.retry_available,
          failedAt: new Date()
        })
        
        return {
          ...prev,
          generatingSpecs: newGeneratingSpecs,
          errors: newErrors
        }
      })
    })

    // Listen for cancellation events
    socket.on('spec.generation.cancelled', (data: {
      job_id: number
      item_id: string
      message?: string
    }) => {
      setState(prev => {
        const newGeneratingSpecs = new Map(prev.generatingSpecs)
        newGeneratingSpecs.delete(data.item_id)
        
        return { ...prev, generatingSpecs: newGeneratingSpecs }
      })
    })

    return () => {
      socket.disconnect()
      socketRef.current = null
    }
  }, [])

  // Start spec generation
  const startGeneration = useCallback(async (itemId: string, provider: string): Promise<number> => {
    try {
      // Check if already generating
      if (state.generatingSpecs.has(itemId)) {
        throw new Error('Spec generation already in progress for this idea')
      }
      
      // Clear any previous errors or completed status
      setState(prev => {
        const newErrors = new Map(prev.errors)
        const newCompletedSpecs = new Map(prev.completedSpecs)
        newErrors.delete(itemId)
        newCompletedSpecs.delete(itemId)
        
        return { ...prev, errors: newErrors, completedSpecs: newCompletedSpecs }
      })
      
      // Start async generation
      const result = await missionControlApi.createSpecificationAsync(
        itemId,
        projectIdRef.current,
        provider
      )
      
      // Add to generating specs
      setState(prev => {
        const newGeneratingSpecs = new Map(prev.generatingSpecs)
        newGeneratingSpecs.set(itemId, {
          jobId: result.job_id,
          itemId,
          provider,
          status: result.status as any,
          progress: 0,
          stage: 'initializing',
          message: 'Starting spec generation...',
          startedAt: new Date(),
          estimatedCompletion: result.estimated_duration
        })
        
        return { ...prev, generatingSpecs: newGeneratingSpecs }
      })
      
      return result.job_id
      
    } catch (error) {
      console.error('Failed to start spec generation:', error)
      
      // Add to errors
      setState(prev => {
        const newErrors = new Map(prev.errors)
        newErrors.set(itemId, {
          error: error instanceof Error ? error.message : 'Failed to start spec generation',
          retryAvailable: true,
          failedAt: new Date()
        })
        
        return { ...prev, errors: newErrors }
      })
      
      throw error
    }
  }, [state.generatingSpecs])

  // Cancel spec generation
  const cancelGeneration = useCallback(async (itemId: string): Promise<boolean> => {
    try {
      const job = state.generatingSpecs.get(itemId)
      if (!job) {
        return false
      }
      
      await missionControlApi.cancelJob(job.jobId)
      
      // Remove from generating specs (WebSocket event will also handle this)
      setState(prev => {
        const newGeneratingSpecs = new Map(prev.generatingSpecs)
        newGeneratingSpecs.delete(itemId)
        
        return { ...prev, generatingSpecs: newGeneratingSpecs }
      })
      
      return true
      
    } catch (error) {
      console.error('Failed to cancel spec generation:', error)
      return false
    }
  }, [state.generatingSpecs])

  // Retry spec generation
  const retryGeneration = useCallback(async (itemId: string, provider?: string): Promise<number> => {
    // Clear error first
    setState(prev => {
      const newErrors = new Map(prev.errors)
      newErrors.delete(itemId)
      return { ...prev, errors: newErrors }
    })
    
    // Use the same provider as before if not specified
    const errorInfo = state.errors.get(itemId)
    const existingJob = state.generatingSpecs.get(itemId)
    const providerToUse = provider || existingJob?.provider || 'claude'
    
    return startGeneration(itemId, providerToUse)
  }, [state.errors, state.generatingSpecs, startGeneration])

  // Clear error
  const clearError = useCallback((itemId: string) => {
    setState(prev => {
      const newErrors = new Map(prev.errors)
      newErrors.delete(itemId)
      return { ...prev, errors: newErrors }
    })
  }, [])

  // Clear completed status
  const clearCompleted = useCallback((itemId: string) => {
    setState(prev => {
      const newCompletedSpecs = new Map(prev.completedSpecs)
      newCompletedSpecs.delete(itemId)
      return { ...prev, completedSpecs: newCompletedSpecs }
    })
  }, [])

  // Utility functions
  const isGenerating = useCallback((itemId: string): boolean => {
    return state.generatingSpecs.has(itemId)
  }, [state.generatingSpecs])

  const getGenerationStatus = useCallback((itemId: string): GenerationJob | null => {
    return state.generatingSpecs.get(itemId) || null
  }, [state.generatingSpecs])

  const hasError = useCallback((itemId: string): boolean => {
    return state.errors.has(itemId)
  }, [state.errors])

  const isCompleted = useCallback((itemId: string): boolean => {
    return state.completedSpecs.has(itemId)
  }, [state.completedSpecs])

  const getActiveGenerationsCount = useCallback((): number => {
    return state.generatingSpecs.size
  }, [state.generatingSpecs])

  return {
    generatingSpecs: state.generatingSpecs,
    isConnected: state.isConnected,
    errors: state.errors,
    completedSpecs: state.completedSpecs,
    startGeneration,
    cancelGeneration,
    retryGeneration,
    clearError,
    clearCompleted,
    isGenerating,
    getGenerationStatus,
    hasError,
    isCompleted,
    getActiveGenerationsCount
  }
}