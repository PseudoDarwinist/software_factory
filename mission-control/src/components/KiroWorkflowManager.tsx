/**
 * KiroWorkflowManager - Step-by-step Kiro specification workflow
 * 
 * This component manages the Kiro workflow for generating specifications
 * in a step-by-step manner with approval gates between each phase.
 * 
 * Features:
 * - Step-by-step workflow (requirements → design → tasks)
 * - Approval buttons for each step transition
 * - Display generated content in appropriate sections
 * - Loading states and error handling
 * - Repository context integration
 * 
 * Requirements addressed:
 * - 2.3: Step-by-step workflow with approval gates
 * - 2.5: User approval before proceeding to next step
 * - 5.1: Progress indicators for workflow steps
 * - 5.2: Clear action buttons for approval
 * - 5.3: Loading indicators during generation
 * - 5.4: Error messages with fallback options
 */

import React, { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { missionControlApi } from '@/services/api/missionControlApi'
import type { FeedItem } from '@/types'

export type WorkflowStep = 'requirements' | 'design' | 'tasks' | 'complete'

export interface KiroWorkflowState {
  currentStep: WorkflowStep
  isGenerating: boolean
  generatedContent: {
    requirements?: string
    design?: string
    tasks?: string
  }
  error?: string
}

export interface GeneratedSpecs {
  requirements: string
  design: string
  tasks: string
}

export interface KiroWorkflowManagerProps {
  projectId: string
  ideaContent: string
  feedItem: FeedItem
  onComplete: (specs: GeneratedSpecs) => void
  onClose: () => void
  className?: string
}

export const KiroWorkflowManager: React.FC<KiroWorkflowManagerProps> = ({
  projectId,
  ideaContent,
  feedItem,
  onComplete,
  onClose,
  className
}) => {
  const [workflowState, setWorkflowState] = useState<KiroWorkflowState>({
    currentStep: 'requirements',
    isGenerating: false,
    generatedContent: {},
    error: undefined
  })

  const [kiroAvailable, setKiroAvailable] = useState<boolean | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const maxRetries = 3

  // Check Kiro availability on mount
  useEffect(() => {
    checkKiroAvailability()
  }, [])

  const checkKiroAvailability = async () => {
    try {
      console.log('🔍 KiroWorkflowManager: Checking Kiro availability...')
      
      // Use direct fetch like DefineStage does
      const response = await fetch('/api/kiro/status')
      const data = await response.json()
      
      console.log('📡 KiroWorkflowManager: Kiro response:', data)
      
      const available = data.success && data.available
      setKiroAvailable(available)
      
      if (!available) {
        setWorkflowState(prev => ({
          ...prev,
          error: 'Kiro IDE is not available. Please ensure Kiro is installed and accessible.'
        }))
      }
    } catch (error) {
      console.error('❌ KiroWorkflowManager: Failed to check Kiro availability:', error)
      setKiroAvailable(false)
      setWorkflowState(prev => ({
        ...prev,
        error: 'Unable to check Kiro availability. Please try again.'
      }))
    }
  }

  const generateRequirements = useCallback(async () => {
    if (!kiroAvailable) return

    setWorkflowState(prev => ({
      ...prev,
      isGenerating: true,
      error: undefined
    }))

    try {
      const result = await missionControlApi.generateRequirementsWithKiro(
        projectId,
        ideaContent
      )

      if (result.success && result.content) {
        setWorkflowState(prev => ({
          ...prev,
          isGenerating: false,
          generatedContent: {
            ...prev.generatedContent,
            requirements: result.content
          }
        }))
        setRetryCount(0)
      } else {
        throw new Error(result.error || 'Failed to generate requirements')
      }
    } catch (error) {
      console.error('Error generating requirements:', error)
      setWorkflowState(prev => ({
        ...prev,
        isGenerating: false,
        error: `Failed to generate requirements: ${error instanceof Error ? error.message : 'Unknown error'}`
      }))
    }
  }, [kiroAvailable, projectId, ideaContent])

  const generateDesign = useCallback(async () => {
    if (!kiroAvailable || !workflowState.generatedContent.requirements) return

    setWorkflowState(prev => ({
      ...prev,
      isGenerating: true,
      error: undefined
    }))

    try {
      const result = await missionControlApi.generateDesignWithKiro(
        projectId,
        ideaContent,
        workflowState.generatedContent.requirements!
      )

      if (result.success && result.content) {
        setWorkflowState(prev => ({
          ...prev,
          isGenerating: false,
          generatedContent: {
            ...prev.generatedContent,
            design: result.content
          }
        }))
        setRetryCount(0)
      } else {
        throw new Error(result.error || 'Failed to generate design')
      }
    } catch (error) {
      console.error('Error generating design:', error)
      setWorkflowState(prev => ({
        ...prev,
        isGenerating: false,
        error: `Failed to generate design: ${error instanceof Error ? error.message : 'Unknown error'}`
      }))
    }
  }, [kiroAvailable, projectId, ideaContent, workflowState.generatedContent.requirements])

  const generateTasks = useCallback(async () => {
    if (!kiroAvailable || !workflowState.generatedContent.requirements || !workflowState.generatedContent.design) return

    setWorkflowState(prev => ({
      ...prev,
      isGenerating: true,
      error: undefined
    }))

    try {
      const result = await missionControlApi.generateTasksWithKiro(
        projectId,
        ideaContent,
        workflowState.generatedContent.requirements!,
        workflowState.generatedContent.design!
      )

      if (result.success && result.content) {
        setWorkflowState(prev => ({
          ...prev,
          isGenerating: false,
          currentStep: 'complete',
          generatedContent: {
            ...prev.generatedContent,
            tasks: result.content
          }
        }))
        setRetryCount(0)
      } else {
        throw new Error(result.error || 'Failed to generate tasks')
      }
    } catch (error) {
      console.error('Error generating tasks:', error)
      setWorkflowState(prev => ({
        ...prev,
        isGenerating: false,
        error: `Failed to generate tasks: ${error instanceof Error ? error.message : 'Unknown error'}`
      }))
    }
  }, [kiroAvailable, projectId, ideaContent, workflowState.generatedContent.requirements, workflowState.generatedContent.design])

  const handleApproveRequirements = () => {
    setWorkflowState(prev => ({
      ...prev,
      currentStep: 'design'
    }))
    generateDesign()
  }

  const handleApproveDesign = () => {
    setWorkflowState(prev => ({
      ...prev,
      currentStep: 'tasks'
    }))
    generateTasks()
  }

  const handleComplete = () => {
    if (workflowState.generatedContent.requirements && 
        workflowState.generatedContent.design && 
        workflowState.generatedContent.tasks) {
      onComplete({
        requirements: workflowState.generatedContent.requirements,
        design: workflowState.generatedContent.design,
        tasks: workflowState.generatedContent.tasks
      })
    }
  }

  const handleRetry = () => {
    if (retryCount >= maxRetries) {
      setWorkflowState(prev => ({
        ...prev,
        error: 'Maximum retry attempts reached. Please try again later or use Claude Code as fallback.'
      }))
      return
    }

    setRetryCount(prev => prev + 1)
    setWorkflowState(prev => ({
      ...prev,
      error: undefined
    }))

    // Retry the current step
    switch (workflowState.currentStep) {
      case 'requirements':
        generateRequirements()
        break
      case 'design':
        generateDesign()
        break
      case 'tasks':
        generateTasks()
        break
    }
  }

  const handleFallbackToClaude = () => {
    // Close Kiro workflow and let user use Claude Code
    onClose()
    // Could emit an event or call a callback to switch to Claude Code
  }

  // Auto-start requirements generation when Kiro is available
  useEffect(() => {
    if (kiroAvailable && workflowState.currentStep === 'requirements' && !workflowState.generatedContent.requirements && !workflowState.isGenerating) {
      generateRequirements()
    }
  }, [kiroAvailable, workflowState.currentStep, workflowState.generatedContent.requirements, workflowState.isGenerating, generateRequirements])

  const getStepStatus = (step: WorkflowStep) => {
    if (workflowState.currentStep === step && workflowState.isGenerating) {
      return 'generating'
    }
    if (workflowState.currentStep === step && workflowState.error) {
      return 'error'
    }
    if (workflowState.generatedContent[step as keyof typeof workflowState.generatedContent]) {
      return 'completed'
    }
    if (workflowState.currentStep === step) {
      return 'current'
    }
    return 'pending'
  }

  const getStepIcon = (step: WorkflowStep) => {
    const status = getStepStatus(step)
    switch (status) {
      case 'generating':
        return '⏳'
      case 'error':
        return '❌'
      case 'completed':
        return '✅'
      case 'current':
        return '🔄'
      default:
        return '⚪'
    }
  }

  const getProgressPercentage = () => {
    const steps = ['requirements', 'design', 'tasks'] as const
    const completedSteps = steps.filter(step => workflowState.generatedContent[step]).length
    return Math.round((completedSteps / steps.length) * 100)
  }

  if (kiroAvailable === false) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className={clsx(
          'fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50',
          className
        )}
      >
        <div className="bg-black/80 backdrop-blur-md border border-white/20 rounded-xl p-6 max-w-md w-full mx-4">
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/20 flex items-center justify-center">
              <span className="text-red-400 text-2xl">⚡</span>
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">Kiro Not Available</h3>
            <p className="text-white/70 text-sm mb-6">
              Kiro IDE is not installed or not accessible. Please install Kiro to use this workflow.
            </p>
            <div className="flex space-x-3">
              <button
                onClick={handleFallbackToClaude}
                className="flex-1 px-4 py-2 bg-blue-500/20 text-blue-400 rounded-lg border border-blue-500/30 hover:bg-blue-500/30 transition-all"
              >
                Use Claude Code
              </button>
              <button
                onClick={onClose}
                className="flex-1 px-4 py-2 bg-white/10 text-white rounded-lg hover:bg-white/20 transition-all"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className={clsx(
        'fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4',
        className
      )}
    >
      <div className="bg-black/90 backdrop-blur-md border border-white/20 rounded-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-white/10">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
                <span className="text-purple-400 text-lg">⚡</span>
              </div>
              <div>
                <h2 className="text-xl font-semibold text-white">Kiro Workflow</h2>
                <p className="text-white/60 text-sm">Step-by-step specification generation</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-all"
            >
              <span className="text-white/70">✕</span>
            </button>
          </div>

          {/* Progress Bar */}
          <div className="mt-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-white/70">Progress</span>
              <span className="text-sm text-white/70">{getProgressPercentage()}%</span>
            </div>
            <div className="h-2 bg-white/10 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-gradient-to-r from-purple-500 to-blue-500"
                initial={{ width: 0 }}
                animate={{ width: `${getProgressPercentage()}%` }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
              />
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex">
          {/* Steps Sidebar */}
          <div className="w-64 bg-black/20 border-r border-white/10 p-4">
            <h3 className="text-sm font-medium text-white/80 mb-4">Workflow Steps</h3>
            <div className="space-y-3">
              {[
                { key: 'requirements' as const, label: 'Requirements', description: 'Analyze repository and generate requirements.md' },
                { key: 'design' as const, label: 'Design', description: 'Create technical design based on requirements' },
                { key: 'tasks' as const, label: 'Tasks', description: 'Generate implementation tasks' }
              ].map((step) => {
                const status = getStepStatus(step.key)
                const icon = getStepIcon(step.key)
                
                return (
                  <div
                    key={step.key}
                    className={clsx(
                      'p-3 rounded-lg border transition-all',
                      status === 'current' && 'bg-purple-500/20 border-purple-500/30',
                      status === 'completed' && 'bg-green-500/20 border-green-500/30',
                      status === 'error' && 'bg-red-500/20 border-red-500/30',
                      status === 'generating' && 'bg-blue-500/20 border-blue-500/30',
                      status === 'pending' && 'bg-white/5 border-white/10'
                    )}
                  >
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="text-lg">{icon}</span>
                      <span className="text-sm font-medium text-white">{step.label}</span>
                    </div>
                    <p className="text-xs text-white/60">{step.description}</p>
                    {status === 'generating' && (
                      <div className="mt-2 flex items-center space-x-2">
                        <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span className="text-xs text-white/70">Generating...</span>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Main Content */}
          <div className="flex-1 flex flex-col">
            {/* Current Step Content */}
            <div className="flex-1 overflow-y-auto p-6">
              <AnimatePresence mode="wait">
                {workflowState.error ? (
                  <motion.div
                    key="error"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -20 }}
                    className="text-center py-8"
                  >
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/20 flex items-center justify-center">
                      <span className="text-red-400 text-2xl">❌</span>
                    </div>
                    <h3 className="text-lg font-semibold text-white mb-2">Generation Failed</h3>
                    <p className="text-white/70 text-sm mb-6 max-w-md mx-auto">
                      {workflowState.error}
                    </p>
                    <div className="flex justify-center space-x-3">
                      {retryCount < maxRetries && (
                        <button
                          onClick={handleRetry}
                          className="px-4 py-2 bg-blue-500/20 text-blue-400 rounded-lg border border-blue-500/30 hover:bg-blue-500/30 transition-all"
                        >
                          Retry ({maxRetries - retryCount} left)
                        </button>
                      )}
                      <button
                        onClick={handleFallbackToClaude}
                        className="px-4 py-2 bg-green-500/20 text-green-400 rounded-lg border border-green-500/30 hover:bg-green-500/30 transition-all"
                      >
                        Use Claude Code
                      </button>
                    </div>
                  </motion.div>
                ) : (
                  <motion.div
                    key={workflowState.currentStep}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    className="h-full"
                  >
                    {workflowState.currentStep === 'requirements' && (
                      <StepContent
                        title="Requirements Generation"
                        description="Analyzing your repository and generating requirements.md based on your idea and existing codebase patterns."
                        content={workflowState.generatedContent.requirements}
                        isGenerating={workflowState.isGenerating}
                        onApprove={handleApproveRequirements}
                        approveButtonText="Approve & Generate Design"
                        canApprove={!!workflowState.generatedContent.requirements && !workflowState.isGenerating}
                      />
                    )}
                    
                    {workflowState.currentStep === 'design' && (
                      <StepContent
                        title="Design Generation"
                        description="Creating technical design document based on the approved requirements and repository analysis."
                        content={workflowState.generatedContent.design}
                        isGenerating={workflowState.isGenerating}
                        onApprove={handleApproveDesign}
                        approveButtonText="Approve & Generate Tasks"
                        canApprove={!!workflowState.generatedContent.design && !workflowState.isGenerating}
                      />
                    )}
                    
                    {workflowState.currentStep === 'tasks' && (
                      <StepContent
                        title="Tasks Generation"
                        description="Generating implementation tasks based on the approved requirements and design."
                        content={workflowState.generatedContent.tasks}
                        isGenerating={workflowState.isGenerating}
                        onApprove={handleComplete}
                        approveButtonText="Complete Workflow"
                        canApprove={!!workflowState.generatedContent.tasks && !workflowState.isGenerating}
                      />
                    )}
                    
                    {workflowState.currentStep === 'complete' && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="text-center py-8"
                      >
                        <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-500/20 flex items-center justify-center">
                          <span className="text-green-400 text-2xl">🎉</span>
                        </div>
                        <h3 className="text-lg font-semibold text-white mb-2">Workflow Complete!</h3>
                        <p className="text-white/70 text-sm mb-6">
                          All specification documents have been generated successfully.
                        </p>
                        <button
                          onClick={handleComplete}
                          className="px-6 py-3 bg-green-500/20 text-green-400 rounded-lg border border-green-500/30 hover:bg-green-500/30 transition-all font-medium"
                        >
                          Finish & Save Specs
                        </button>
                      </motion.div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}

interface StepContentProps {
  title: string
  description: string
  content?: string
  isGenerating: boolean
  onApprove: () => void
  approveButtonText: string
  canApprove: boolean
}

const StepContent: React.FC<StepContentProps> = ({
  title,
  description,
  content,
  isGenerating,
  onApprove,
  approveButtonText,
  canApprove
}) => {
  return (
    <div className="h-full flex flex-col">
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
        <p className="text-white/70 text-sm">{description}</p>
      </div>

      <div className="flex-1 flex flex-col">
        {isGenerating ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-blue-500/20 flex items-center justify-center">
                <div className="w-6 h-6 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin" />
              </div>
              <h4 className="text-white font-medium mb-2">Generating Content</h4>
              <p className="text-white/60 text-sm">
                Kiro is analyzing your repository and generating the specification...
              </p>
            </div>
          </div>
        ) : content ? (
          <>
            <div className="flex-1 bg-white/5 border border-white/10 rounded-lg p-4 overflow-y-auto">
              <pre className="text-white text-sm whitespace-pre-wrap font-mono leading-relaxed">
                {content}
              </pre>
            </div>
            <div className="mt-4 flex justify-end">
              <motion.button
                whileHover={{ scale: canApprove ? 1.05 : 1 }}
                whileTap={{ scale: canApprove ? 0.95 : 1 }}
                onClick={onApprove}
                disabled={!canApprove}
                className={clsx(
                  'px-6 py-3 rounded-lg font-medium transition-all',
                  canApprove
                    ? 'bg-green-500/20 text-green-400 border border-green-500/30 hover:bg-green-500/30'
                    : 'bg-gray-500/20 text-gray-400 border border-gray-500/30 cursor-not-allowed'
                )}
              >
                {approveButtonText}
              </motion.button>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center text-white/60">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-white/5 flex items-center justify-center">
                <span className="text-white/40 text-2xl">📝</span>
              </div>
              <h4 className="text-sm font-medium mb-2">Waiting for Generation</h4>
              <p className="text-xs">
                Content will appear here once generation is complete
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default KiroWorkflowManager