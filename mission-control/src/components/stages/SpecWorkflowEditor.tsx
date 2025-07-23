/**
 * SpecWorkflowEditor - Implements the exact same workflow as Kiro's internal spec process
 * 
 * Workflow:
 * 1. Requirements Phase - Generate requirements.md, get user approval
 * 2. Design Phase - Generate design.md based on requirements, get user approval  
 * 3. Tasks Phase - Generate tasks.md based on requirements + design, get user approval
 * 
 * Each phase requires explicit user approval before proceeding to the next phase.
 * This mirrors exactly how Kiro creates specifications internally.
 */

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { missionControlApi } from '@/services/api/missionControlApi'
import type { FeedItem } from '@/types'

interface SpecWorkflowEditorProps {
  feedItem: FeedItem
  projectId: string
  onComplete: () => void
  onClose: () => void
}

type WorkflowPhase = 'requirements' | 'design' | 'tasks' | 'complete'
type PhaseStatus = 'not_started' | 'generating' | 'awaiting_approval' | 'approved' | 'completed'

interface PhaseData {
  content: string
  status: PhaseStatus
  lastModified: string
}

interface WorkflowState {
  currentPhase: WorkflowPhase
  phases: Record<'requirements' | 'design' | 'tasks', PhaseData>
  userFeedback: string
  isProcessingFeedback: boolean
}

const PHASE_CONFIG = {
  requirements: {
    title: 'Requirements',
    description: 'Define functional and non-functional requirements',
    icon: '📋',
    color: 'blue',
    approvalPrompt: 'Do the requirements look good? If so, we can move on to the design.',
    generatePrompt: (ideaContent: string, _context?: string) => `Generate a comprehensive requirements.md document for this feature idea:

${ideaContent}

Create a markdown document with:

## Introduction
[Brief overview of the feature]

## Requirements

### Requirement 1
**User Story:** As a [role], I want [feature], so that [benefit]

#### Acceptance Criteria
1. WHEN [event] THEN [system] SHALL [response]
2. IF [precondition] THEN [system] SHALL [response]

### Requirement 2
**User Story:** As a [role], I want [feature], so that [benefit]

#### Acceptance Criteria
1. WHEN [event] THEN [system] SHALL [response]
2. WHEN [event] AND [condition] THEN [system] SHALL [response]

Use EARS format (Easy Approach to Requirements Syntax) for acceptance criteria.
Include edge cases, user experience, technical constraints, and success criteria.`
  },
  design: {
    title: 'Design',
    description: 'Create technical architecture and system design',
    icon: '🎨',
    color: 'purple',
    approvalPrompt: 'Does the design look good? If so, we can move on to the implementation plan.',
    generatePrompt: (ideaContent: string, requirements?: string) => `Generate a comprehensive design.md document for this feature:

${ideaContent}

Based on these requirements:
${requirements}

Create a markdown document with:

## Overview
[High-level design summary]

## Architecture
[System architecture and components]

## Components and Interfaces
[Detailed component design]

## Data Models
[Database schema and data structures]

## Error Handling
[Error handling strategy]

## Testing Strategy
[Testing approach and considerations]

Include diagrams using Mermaid syntax where appropriate.
Address all requirements from the requirements document.`
  },
  tasks: {
    title: 'Implementation Tasks',
    description: 'Break down into actionable development tasks',
    icon: '✅',
    color: 'green',
    approvalPrompt: 'Do the tasks look good?',
    generatePrompt: (ideaContent: string, requirements?: string, design?: string) => `Generate a comprehensive tasks.md document for this feature:

${ideaContent}

Based on these requirements:
${requirements}

And this design:
${design}

Convert the feature design into a series of prompts for a code-generation LLM that will implement each step in a test-driven manner. Prioritize best practices, incremental progress, and early testing, ensuring no big jumps in complexity at any stage. Make sure that each prompt builds on the previous prompts, and ends with wiring things together. There should be no hanging or orphaned code that isn't integrated into a previous step. Focus ONLY on tasks that involve writing, modifying, or testing code.

Format as:

# Implementation Plan

- [ ] 1. Set up project structure and core interfaces
  - Create directory structure for models, services, repositories, and API components
  - Define interfaces that establish system boundaries
  - _Requirements: 1.1_

- [ ] 2. Implement data models and validation
- [ ] 2.1 Create core data model interfaces and types
  - Write TypeScript interfaces for all data models
  - Implement validation functions for data integrity
  - _Requirements: 2.1, 3.3, 1.2_

- [ ] 2.2 Implement User model with validation
  - Write User class with validation methods
  - Create unit tests for User model validation
  - _Requirements: 1.2_

Each task must:
- Be a discrete, manageable coding step
- Reference specific requirements
- Build incrementally on previous steps
- Be actionable by a coding agent`
  }
}

export const SpecWorkflowEditor: React.FC<SpecWorkflowEditorProps> = ({
  feedItem,
  projectId,
  onComplete,
  onClose
}) => {
  const [workflowState, setWorkflowState] = useState<WorkflowState>({
    currentPhase: 'requirements',
    phases: {
      requirements: { content: '', status: 'not_started', lastModified: '' },
      design: { content: '', status: 'not_started', lastModified: '' },
      tasks: { content: '', status: 'not_started', lastModified: '' }
    },
    userFeedback: '',
    isProcessingFeedback: false
  })

  // Load existing specification if available
  useEffect(() => {
    loadExistingSpecification()
  }, [feedItem.id, projectId])

  const loadExistingSpecification = async () => {
    try {
      const spec = await missionControlApi.getSpecification(feedItem.id, projectId)
      
      if (spec) {
        const newPhases = { ...workflowState.phases }
        let currentPhase: WorkflowPhase = 'requirements'
        
        // Map artifacts to phases
        if (spec.requirements) {
          newPhases.requirements = {
            content: spec.requirements.content || '',
            status: 'approved',
            lastModified: spec.requirements.updated_at || ''
          }
          currentPhase = 'design'
        }
        
        if (spec.design) {
          newPhases.design = {
            content: spec.design.content || '',
            status: 'approved',
            lastModified: spec.design.updated_at || ''
          }
          currentPhase = 'tasks'
        }
        
        if (spec.tasks) {
          newPhases.tasks = {
            content: spec.tasks.content || '',
            status: 'approved',
            lastModified: spec.tasks.updated_at || ''
          }
          currentPhase = 'complete'
        }
        
        setWorkflowState(prev => ({
          ...prev,
          phases: newPhases,
          currentPhase
        }))
      }
    } catch (error) {
      console.error('Failed to load existing specification:', error)
    }
  }

  const generatePhaseContent = async (phase: 'requirements' | 'design' | 'tasks') => {
    try {
      setWorkflowState(prev => ({
        ...prev,
        phases: {
          ...prev.phases,
          [phase]: { ...prev.phases[phase], status: 'generating' }
        }
      }))

      const config = PHASE_CONFIG[phase]
      const ideaContent = `Title: ${feedItem.title}\n\nDescription: ${feedItem.summary || 'No description provided'}`
      
      let prompt = ''
      if (phase === 'requirements') {
        prompt = config.generatePrompt(ideaContent)
      } else if (phase === 'design') {
        prompt = config.generatePrompt(ideaContent, workflowState.phases.requirements.content)
      } else if (phase === 'tasks') {
        prompt = config.generatePrompt(
          ideaContent, 
          workflowState.phases.requirements.content,
          workflowState.phases.design.content
        )
      }

      // Call AI to generate content
      const response = await callAI(prompt)
      
      const now = new Date().toISOString()
      
      setWorkflowState(prev => ({
        ...prev,
        phases: {
          ...prev.phases,
          [phase]: {
            content: response,
            status: 'awaiting_approval',
            lastModified: now
          }
        }
      }))

      // Save to backend
      await missionControlApi.updateSpecificationArtifact(
        `spec_${feedItem.id}`,
        projectId,
        phase,
        response
      )

    } catch (error) {
      console.error(`Failed to generate ${phase}:`, error)
      setWorkflowState(prev => ({
        ...prev,
        phases: {
          ...prev.phases,
          [phase]: { ...prev.phases[phase], status: 'not_started' }
        }
      }))
    }
  }

  const callAI = async (prompt: string): Promise<string> => {
    // Use AI Model Garden which is working
    const response = await fetch('/api/model-garden/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        prompt,
        model: 'claude-3-5-sonnet-20241022' // Use the working model
      })
    })
    
    if (!response.ok) {
      throw new Error('AI request failed')
    }
    
    const data = await response.json()
    return data.response || 'No response generated'
  }

  const handleUserApproval = async (approved: boolean) => {
    const currentPhaseKey = workflowState.currentPhase as 'requirements' | 'design' | 'tasks'
    
    if (approved) {
      // Mark current phase as approved
      setWorkflowState(prev => ({
        ...prev,
        phases: {
          ...prev.phases,
          [currentPhaseKey]: { ...prev.phases[currentPhaseKey], status: 'approved' }
        }
      }))

      // Move to next phase
      if (workflowState.currentPhase === 'requirements') {
        setWorkflowState(prev => ({ ...prev, currentPhase: 'design' }))
      } else if (workflowState.currentPhase === 'design') {
        setWorkflowState(prev => ({ ...prev, currentPhase: 'tasks' }))
      } else if (workflowState.currentPhase === 'tasks') {
        setWorkflowState(prev => ({ ...prev, currentPhase: 'complete' }))
        onComplete()
      }
    } else {
      // User wants changes - wait for feedback
      setWorkflowState(prev => ({
        ...prev,
        phases: {
          ...prev.phases,
          [currentPhaseKey]: { ...prev.phases[currentPhaseKey], status: 'awaiting_approval' }
        }
      }))
    }
  }

  const processFeedback = async () => {
    if (!workflowState.userFeedback.trim()) return

    const currentPhaseKey = workflowState.currentPhase as 'requirements' | 'design' | 'tasks'
    const currentContent = workflowState.phases[currentPhaseKey].content

    setWorkflowState(prev => ({ ...prev, isProcessingFeedback: true }))

    try {
      const feedbackPrompt = `You are helping refine a ${workflowState.currentPhase} specification.

Current ${workflowState.currentPhase} content:
${currentContent}

Original idea:
Title: ${feedItem.title}
Description: ${feedItem.summary || 'No description provided'}

User feedback: ${workflowState.userFeedback}

Please provide the updated ${workflowState.currentPhase} content incorporating the user's feedback. Return the complete updated markdown document.`

      const updatedContent = await callAI(feedbackPrompt)

      const now = new Date().toISOString()
      
      setWorkflowState(prev => ({
        ...prev,
        phases: {
          ...prev.phases,
          [currentPhaseKey]: {
            content: updatedContent,
            status: 'awaiting_approval',
            lastModified: now
          }
        },
        userFeedback: '',
        isProcessingFeedback: false
      }))

      // Save updated content to backend
      await missionControlApi.updateSpecificationArtifact(
        `spec_${feedItem.id}`,
        projectId,
        currentPhaseKey,
        updatedContent
      )

    } catch (error) {
      console.error('Failed to process feedback:', error)
      setWorkflowState(prev => ({ ...prev, isProcessingFeedback: false }))
    }
  }

  const updatePhaseContent = async (phase: 'requirements' | 'design' | 'tasks', content: string) => {
    const now = new Date().toISOString()
    
    setWorkflowState(prev => ({
      ...prev,
      phases: {
        ...prev.phases,
        [phase]: {
          ...prev.phases[phase],
          content,
          lastModified: now
        }
      }
    }))

    // Auto-save to backend
    try {
      await missionControlApi.updateSpecificationArtifact(
        `spec_${feedItem.id}`,
        projectId,
        phase,
        content
      )
    } catch (error) {
      console.error('Failed to save changes:', error)
    }
  }

  const currentPhaseKey = workflowState.currentPhase as 'requirements' | 'design' | 'tasks'
  const currentPhaseData = workflowState.currentPhase !== 'complete' ? workflowState.phases[currentPhaseKey] : null
  const config = workflowState.currentPhase !== 'complete' ? PHASE_CONFIG[currentPhaseKey] : null

  if (workflowState.currentPhase === 'complete') {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50"
      >
        <motion.div
          initial={{ y: 50 }}
          animate={{ y: 0 }}
          className="bg-black/80 backdrop-blur-md border border-white/20 rounded-xl p-8 max-w-md w-full mx-4 text-center"
        >
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-500/20 flex items-center justify-center">
            <span className="text-2xl">✅</span>
          </div>
          <h2 className="text-2xl font-bold text-white mb-4">Specification Complete!</h2>
          <p className="text-white/70 mb-6">
            All phases have been completed and approved. The specification is ready for implementation.
          </p>
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-blue-500/20 text-blue-400 rounded-lg border border-blue-500/30 hover:bg-blue-500/30 transition-all"
            >
              Close
            </button>
          </div>
        </motion.div>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ y: 50 }}
        animate={{ y: 0 }}
        className="w-full h-full max-w-6xl max-h-[90vh] bg-black/80 backdrop-blur-md border border-white/20 rounded-xl overflow-hidden flex"
      >
        {/* Left Sidebar - Phase Progress */}
        <div className="w-64 bg-black/40 border-r border-white/10 p-4">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-white">Spec Workflow</h2>
            <button
              onClick={onClose}
              className="text-white/60 hover:text-white transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Phase Progress */}
          <div className="space-y-3">
            {(Object.keys(PHASE_CONFIG) as Array<'requirements' | 'design' | 'tasks'>).map((phase) => {
              const phaseConfig = PHASE_CONFIG[phase]
              const phaseData = workflowState.phases[phase]
              const isActive = workflowState.currentPhase === phase
              const isCompleted = phaseData.status === 'approved'
              const isGenerating = phaseData.status === 'generating'
              const isAwaitingApproval = phaseData.status === 'awaiting_approval'

              return (
                <div
                  key={phase}
                  className={clsx(
                    'p-3 rounded-lg border',
                    isActive && 'bg-white/10 border-white/20 text-white',
                    !isActive && isCompleted && 'bg-green-500/10 border-green-500/30 text-green-400',
                    !isActive && !isCompleted && 'bg-white/5 border-white/10 text-white/60',
                    isGenerating && 'opacity-50'
                  )}
                >
                  <div className="flex items-center space-x-3">
                    <div className={clsx(
                      'w-8 h-8 rounded-full flex items-center justify-center text-sm',
                      isCompleted && 'bg-green-500/20',
                      isAwaitingApproval && 'bg-yellow-500/20',
                      isGenerating && 'bg-blue-500/20',
                      !isCompleted && !isAwaitingApproval && !isGenerating && 'bg-white/10'
                    )}>
                      {isCompleted ? '✓' : 
                       isAwaitingApproval ? '⏳' :
                       isGenerating ? '⚡' : 
                       phaseConfig.icon}
                    </div>
                    <div className="flex-1">
                      <div className="font-medium text-sm">{phaseConfig.title}</div>
                      <div className="text-xs opacity-70">
                        {isGenerating ? 'Generating...' :
                         isAwaitingApproval ? 'Awaiting approval' :
                         isCompleted ? 'Approved' :
                         'Not started'}
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col">
          {/* Header */}
          <div className="p-6 border-b border-white/10">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold text-white mb-2 flex items-center space-x-3">
                  <span>{config?.icon}</span>
                  <span>{config?.title}</span>
                </h1>
                <p className="text-white/70 text-sm mb-2">{config?.description}</p>
                <div className="text-xs text-white/50">
                  Idea: {feedItem.title}
                </div>
              </div>
              
              <div className="flex items-center space-x-3">
                {currentPhaseData?.status === 'not_started' && (
                  <motion.button
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => generatePhaseContent(currentPhaseKey)}
                    className={clsx(
                      'px-6 py-2 rounded-lg font-medium transition-all',
                      `bg-${config?.color}-500/20 text-${config?.color}-400 border border-${config?.color}-500/30 hover:bg-${config?.color}-500/30`
                    )}
                  >
                    Generate {config?.title}
                  </motion.button>
                )}
              </div>
            </div>
          </div>

          {/* Content Area */}
          <div className="flex-1 flex flex-col">
            {currentPhaseData?.status === 'generating' ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-white/10 flex items-center justify-center">
                    <svg className="w-6 h-6 animate-spin text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </div>
                  <p className="text-white/80">Generating {config?.title}...</p>
                  <p className="text-white/60 text-sm mt-2">This may take a few minutes</p>
                </div>
              </div>
            ) : currentPhaseData?.content ? (
              <div className="flex-1 flex flex-col">
                {/* Editor */}
                <div className="flex-1">
                  <textarea
                    value={currentPhaseData.content}
                    onChange={(e) => updatePhaseContent(currentPhaseKey, e.target.value)}
                    className="w-full h-full p-6 bg-transparent text-white placeholder-white/50 focus:outline-none resize-none font-mono text-sm"
                    placeholder={`Enter ${config?.title.toLowerCase()} content...`}
                    disabled={currentPhaseData.status === 'approved'}
                  />
                </div>

                {/* Approval Section */}
                {currentPhaseData.status === 'awaiting_approval' && (
                  <div className="border-t border-white/10 p-6 bg-black/20">
                    <div className="mb-4">
                      <h3 className="text-lg font-semibold text-white mb-2">
                        {config?.approvalPrompt}
                      </h3>
                      <div className="flex space-x-3">
                        <motion.button
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                          onClick={() => handleUserApproval(true)}
                          className="px-6 py-2 bg-green-500/20 text-green-400 rounded-lg border border-green-500/30 hover:bg-green-500/30 transition-all font-medium"
                        >
                          Yes, looks good
                        </motion.button>
                        <motion.button
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                          onClick={() => handleUserApproval(false)}
                          className="px-6 py-2 bg-yellow-500/20 text-yellow-400 rounded-lg border border-yellow-500/30 hover:bg-yellow-500/30 transition-all font-medium"
                        >
                          Needs changes
                        </motion.button>
                      </div>
                    </div>

                    {/* Feedback Input */}
                    <div className="space-y-3">
                      <label className="block text-sm font-medium text-white/80">
                        Feedback (optional):
                      </label>
                      <div className="flex space-x-2">
                        <input
                          type="text"
                          value={workflowState.userFeedback}
                          onChange={(e) => setWorkflowState(prev => ({ ...prev, userFeedback: e.target.value }))}
                          placeholder="What changes would you like to see?"
                          className="flex-1 px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-500/50 text-sm"
                          disabled={workflowState.isProcessingFeedback}
                        />
                        <motion.button
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                          onClick={processFeedback}
                          disabled={!workflowState.userFeedback.trim() || workflowState.isProcessingFeedback}
                          className="px-4 py-2 bg-blue-500/20 text-blue-400 rounded-lg border border-blue-500/30 hover:bg-blue-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {workflowState.isProcessingFeedback ? 'Processing...' : 'Apply Changes'}
                        </motion.button>
                      </div>
                    </div>
                  </div>
                )}

                {/* Approved State */}
                {currentPhaseData.status === 'approved' && (
                  <div className="border-t border-white/10 p-6 bg-green-500/10">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 rounded-full bg-green-500/20 flex items-center justify-center">
                        <span className="text-green-400">✓</span>
                      </div>
                      <div>
                        <h3 className="text-lg font-semibold text-green-400">
                          {config?.title} Approved
                        </h3>
                        <p className="text-green-400/70 text-sm">
                          Ready to proceed to the next phase
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center text-white/60">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-white/5 flex items-center justify-center">
                    <span className="text-2xl">{config?.icon}</span>
                  </div>
                  <h3 className="text-lg font-medium mb-2">Ready to create {config?.title}</h3>
                  <p className="text-sm mb-4">
                    Click "Generate {config?.title}" to create AI-powered content
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}