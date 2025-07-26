/**
 * DefineStage - AI-powered specification editor with three-tab interface
 * 
 * This component implements the Define stage with:
 * 1. Left side shows "Ideas in Definition" 
 * 2. Right side shows three-tab editor (Requirements, Design, Tasks)
 * 3. AI-draft vs Human-reviewed badge system
 * 4. Freeze specification workflow with validation
 * 5. Context-aware AI assistant integration
 * 
 * Features:
 * - Three-tab editor for requirements.md, design.md, tasks.md
 * - Badge system showing AI-draft (🟡) vs Human-reviewed (🟢) status
 * - Freeze Spec button that emits spec.frozen event
 * - Real-time collaboration and auto-save
 * - Context-aware AI assistant for specification help
 */

import React, { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { LiquidCard } from '@/components/core/LiquidCard'

import { missionControlApi } from '@/services/api/missionControlApi'
import { SpecWorkflowEditor } from './SpecWorkflowEditor'
import { AssistantSelector, type AssistantType } from '@/components/AssistantSelector'
import { KiroWorkflowManager, type GeneratedSpecs } from '@/components/KiroWorkflowManager'
import type { FeedItem, SDLCStage } from '@/types'
import { io as socketIOClient } from 'socket.io-client'

interface DefineStageProps {
  feedItems: FeedItem[]
  selectedProject: string | null
  selectedFeedItem: string | null
  onFeedItemSelect: (feedItemId: string | null) => void
  onStageChange: (stage: SDLCStage) => void
  loading: boolean
  error: string | null
}

interface SpecificationArtifact {
  id: string
  spec_id: string
  project_id: number
  artifact_type: 'requirements' | 'design' | 'tasks'
  content: string
  status: 'ai_draft' | 'human_reviewed' | 'frozen'
  version: number
  created_by: string
  created_at: string
  updated_by: string
  updated_at: string
  ai_generated: boolean
  ai_model_used: string | null
  context_sources: string[]
  reviewed_by: string | null
  reviewed_at: string | null
  review_notes: string | null
}

interface SpecificationSet {
  spec_id: string
  project_id: number
  requirements?: SpecificationArtifact
  design?: SpecificationArtifact
  tasks?: SpecificationArtifact
  completion_status: {
    complete: boolean
    total_artifacts: number
    ai_draft: number
    human_reviewed: number
    frozen: number
    ready_to_freeze: boolean
  }
}

export const DefineStage: React.FC<DefineStageProps> = ({
  feedItems,
  selectedProject,
  selectedFeedItem,
  onFeedItemSelect,
  onStageChange,
  loading,
  error,
}) => {
  const [ideasInDefinition, setIdeasInDefinition] = useState<FeedItem[]>([])
  const [openAssistantSelector, setOpenAssistantSelector] = useState<string | null>(null)
  const [currentSpec, setCurrentSpec] = useState<SpecificationSet | null>(null)
  const [specLoading, setSpecLoading] = useState(false)
  const [specError, setSpecError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'requirements' | 'design' | 'tasks'>('requirements')
  const [aiAssistantOpen, setAiAssistantOpen] = useState(false)
  const [showProgressiveEditor, setShowProgressiveEditor] = useState(false)
  const [selectedFeedItemForSpec, setSelectedFeedItemForSpec] = useState<FeedItem | null>(null)
  const [selectedAssistant, setSelectedAssistant] = useState<AssistantType>('claude')
  const [showKiroWorkflow, setShowKiroWorkflow] = useState(false)
  const [kiroFeedItem, setKiroFeedItem] = useState<FeedItem | null>(null)
  const [tasksStreamingContent, setTasksStreamingContent] = useState<string>('')
  const [tasksGenerating, setTasksGenerating] = useState(false)

  // Filter ideas that are in definition stage
  useEffect(() => {
    const definitionItems = feedItems.filter(item => 
      item.kind === 'idea' && 
      item.metadata?.stage === 'define'
    )
    setIdeasInDefinition(definitionItems)
  }, [feedItems])

  // Load specification when an item is selected
  useEffect(() => {
    if (selectedFeedItem && selectedProject) {
      loadSpecification(selectedFeedItem, selectedProject)
    } else if (!selectedFeedItem && ideasInDefinition.length > 0 && selectedProject) {
      // Auto-select the first item in definition if none is selected
      const firstItem = ideasInDefinition[0]
      loadSpecification(firstItem.id, selectedProject)
      onFeedItemSelect(firstItem.id)
    } else if (!selectedFeedItem) {
      // Only clear spec if there are no items in definition
      setCurrentSpec(null)
    }
  }, [selectedFeedItem, selectedProject, ideasInDefinition, onFeedItemSelect])

  const loadSpecification = async (itemId: string, projectId: string) => {
    try {
      setSpecLoading(true)
      setSpecError(null)
      
      const spec = await missionControlApi.getSpecification(itemId, projectId)
      setCurrentSpec(spec)
    } catch (error) {
      setSpecError('Failed to load specification')
      console.error('Error loading specification:', error)
    } finally {
      setSpecLoading(false)
    }
  }

  const updateArtifact = useCallback(async (
    artifactType: 'requirements' | 'design' | 'tasks',
    content: string
  ) => {
    if (!currentSpec || !selectedProject) return

    try {
      const updatedArtifact = await missionControlApi.updateSpecificationArtifact(
        currentSpec.spec_id,
        selectedProject,
        artifactType,
        content
      )
      
      setCurrentSpec(prev => {
        if (!prev) return null
        return {
          ...prev,
          [artifactType]: updatedArtifact
        }
      })
    } catch (error) {
      console.error('Error updating artifact:', error)
    }
  }, [currentSpec, selectedProject])

  const markAsHumanReviewed = useCallback(async (
    artifactType: 'requirements' | 'design' | 'tasks',
    reviewNotes?: string
  ) => {
    if (!currentSpec || !selectedProject) return

    try {
      const updatedArtifact = await missionControlApi.markArtifactReviewed(
        currentSpec.spec_id,
        selectedProject,
        artifactType,
        reviewNotes
      )
      
      setCurrentSpec(prev => {
        if (!prev) return null
        return {
          ...prev,
          [artifactType]: updatedArtifact
        }
      })
    } catch (error) {
      console.error('Error marking artifact as reviewed:', error)
    }
  }, [currentSpec, selectedProject])

  const freezeSpecification = useCallback(async () => {
    if (!currentSpec || !selectedProject) return

    try {
      await missionControlApi.freezeSpecification(currentSpec.spec_id, selectedProject)
      
      // Update local state
      setCurrentSpec(prev => {
        if (!prev) return null
        return {
          ...prev,
          requirements: prev.requirements ? { ...prev.requirements, status: 'frozen' } : undefined,
          design: prev.design ? { ...prev.design, status: 'frozen' } : undefined,
          tasks: prev.tasks ? { ...prev.tasks, status: 'frozen' } : undefined,
          completion_status: { ...prev.completion_status, frozen: 3 }
        }
      })
      
      // Transition to Plan stage
      onStageChange('plan')
    } catch (error) {
      console.error('Error freezing specification:', error)
    }
  }, [currentSpec, selectedProject, onStageChange])

  const calculateProgress = useCallback((spec: SpecificationSet) => {
    const { completion_status } = spec
    const total = 3 // requirements, design, tasks
    const completed = completion_status.human_reviewed + completion_status.frozen
    return Math.round((completed / total) * 100)
  }, [])

  const generateDesignDocument = useCallback(async () => {
    if (!currentSpec || !selectedProject) return

    try {
      setSpecLoading(true)
      setSpecError(null)
      
      console.log('Generating design document for spec:', currentSpec.spec_id)
      
      const designArtifact = await missionControlApi.generateDesignDocument(
        currentSpec.spec_id,
        selectedProject
      )
      
      // Update the current spec with the new design artifact
      setCurrentSpec(prev => {
        if (!prev) return null
        return {
          ...prev,
          design: designArtifact
        }
      })
      
      // Switch to design tab to show the generated content
      setActiveTab('design')
      
      console.log('Design document generated successfully')
      
    } catch (error) {
      console.error('Error generating design document:', error)
      setSpecError('Failed to generate design document')
    } finally {
      setSpecLoading(false)
    }
  }, [currentSpec, selectedProject])

  const generateTasksDocument = useCallback(async () => {
    if (!currentSpec || !selectedProject) return

    try {
      setTasksGenerating(true)
      setTasksStreamingContent('')
      // create placeholder artifact
      setCurrentSpec(prev => prev ? { ...prev, tasks: { ...(prev.tasks || {} as any), content: '', status: 'ai_draft' } } : prev)
      // switch to tasks tab immediately
      setActiveTab('tasks')
      await missionControlApi.generateTasksDocument(
        currentSpec.spec_id,
        selectedProject
      )
      // we rely on websocket for progress/done
    } catch (error) {
      console.error('Error generating tasks document:', error)
      setSpecError('Failed to generate tasks document')
      setTasksGenerating(false)
    }
  }, [currentSpec, selectedProject])

  const createSpecification = async (feedItem: FeedItem) => {
    if (!selectedProject) return
    
    try {
      setSpecLoading(true)
      setSpecError(null)
      
      // Call the new Create Spec API endpoint
      const result = await missionControlApi.createSpecification(feedItem.id, selectedProject)
      
      console.log('Specification created:', result)
      
      // Load the newly created specification
      await loadSpecification(feedItem.id, selectedProject)
      
      // Select this feed item
      onFeedItemSelect(feedItem.id)
      
    } catch (error) {
      console.error('Failed to create specification:', error)
      setSpecError('Failed to create specification')
    } finally {
      setSpecLoading(false)
    }
  }

  const createSpecificationWithModelGarden = async (feedItem: FeedItem) => {
    if (!selectedProject) return
    
    try {
      setSpecLoading(true)
      setSpecError(null)
      
      console.log('Creating specification with AI Model Garden for:', feedItem.title)
      
      // Call the AI Model Garden Create Spec API endpoint
      const result = await missionControlApi.createSpecificationWithModelGarden(feedItem.id, selectedProject)
      
      console.log('AI Model Garden specification created:', result)
      
      // Load the newly created specification
      await loadSpecification(feedItem.id, selectedProject)
      
      // Select this feed item
      onFeedItemSelect(feedItem.id)
      
    } catch (error) {
      console.error('Failed to create specification with AI Model Garden:', error)
      setSpecError('Failed to create specification with AI Model Garden')
    } finally {
      setSpecLoading(false)
    }
  }

  const handleAssistantSelect = (assistant: AssistantType, feedItem: FeedItem) => {
    setSelectedAssistant(assistant)
    
    if (assistant === 'claude') {
      // Use existing Claude Code workflow
      createSpecification(feedItem)
    } else if (assistant === 'model-garden') {
      // Use AI Model Garden workflow
      createSpecificationWithModelGarden(feedItem)
    } else if (assistant === 'kiro') {
      // Start Kiro step-by-step workflow (currently disabled)
      setKiroFeedItem(feedItem)
      setShowKiroWorkflow(true)
    }
  }

  const handleKiroWorkflowComplete = async (specs: GeneratedSpecs) => {
    if (!kiroFeedItem || !selectedProject) return

    try {
      setSpecLoading(true)
      setSpecError(null)

      // Create specification with Kiro-generated content
      const result = await missionControlApi.createSpecification(kiroFeedItem.id, selectedProject)
      
      // Update each artifact with the generated content
      await Promise.all([
        missionControlApi.updateSpecificationArtifact(result.spec_id, selectedProject, 'requirements', specs.requirements),
        missionControlApi.updateSpecificationArtifact(result.spec_id, selectedProject, 'design', specs.design),
        missionControlApi.updateSpecificationArtifact(result.spec_id, selectedProject, 'tasks', specs.tasks)
      ])

      // Load the newly created specification
      await loadSpecification(kiroFeedItem.id, selectedProject)
      
      // Select this feed item
      onFeedItemSelect(kiroFeedItem.id)
      
      // Close Kiro workflow
      setShowKiroWorkflow(false)
      setKiroFeedItem(null)
      
    } catch (error) {
      console.error('Failed to save Kiro specifications:', error)
      setSpecError('Failed to save Kiro specifications')
    } finally {
      setSpecLoading(false)
    }
  }

  const handleKiroWorkflowClose = () => {
    setShowKiroWorkflow(false)
    setKiroFeedItem(null)
  }

  const openProgressiveEditor = (feedItem: FeedItem) => {
    setSelectedFeedItemForSpec(feedItem)
    setShowProgressiveEditor(true)
  }

  const closeProgressiveEditor = () => {
    setShowProgressiveEditor(false)
    setSelectedFeedItemForSpec(null)
    // Refresh the specification list
    if (selectedFeedItem && selectedProject) {
      loadSpecification(selectedFeedItem, selectedProject)
    }
  }

  const handlePhaseComplete = (phase: string) => {
    console.log('Phase completed:', phase)
    if (phase === 'all') {
      // All phases completed, close editor and refresh
      closeProgressiveEditor()
    }
  }

  // Resizable pane state
  const [leftPaneWidth, setLeftPaneWidth] = useState(320) // 320px = w-80
  const [rightPaneWidth, setRightPaneWidth] = useState(400) // 400px default
  const [isDraggingLeft, setIsDraggingLeft] = useState(false)
  const [isDraggingRight, setIsDraggingRight] = useState(false)

  // Handle left pane resize
  const handleLeftResize = useCallback((e: MouseEvent) => {
    if (!isDraggingLeft) return
    const newWidth = Math.max(200, Math.min(600, e.clientX))
    setLeftPaneWidth(newWidth)
  }, [isDraggingLeft])

  // Handle right pane resize
  const handleRightResize = useCallback((e: MouseEvent) => {
    if (!isDraggingRight) return
    const newWidth = Math.max(300, Math.min(800, window.innerWidth - e.clientX))
    setRightPaneWidth(newWidth)
  }, [isDraggingRight])

  // Mouse event handlers
  useEffect(() => {
    if (isDraggingLeft || isDraggingRight) {
      const handleMouseMove = isDraggingLeft ? handleLeftResize : handleRightResize
      const handleMouseUp = () => {
        setIsDraggingLeft(false)
        setIsDraggingRight(false)
      }

      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'

      return () => {
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('mouseup', handleMouseUp)
        document.body.style.cursor = ''
        document.body.style.userSelect = ''
      }
    }
  }, [isDraggingLeft, isDraggingRight, handleLeftResize, handleRightResize])

  useEffect(() => {
    if (!currentSpec) return
    const socketUrl = `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`
    const socket = socketIOClient(socketUrl, { transports: ['websocket'] })

    const progressHandler = (data: any) => {
      if (data.spec_id === currentSpec.spec_id) {
        setTasksStreamingContent(prev => prev + data.delta)
      }
    }
    const doneHandler = (data: any) => {
      if (data.spec_id === currentSpec.spec_id) {
        setTasksGenerating(false)
        if (selectedProject) {
          // Correctly extract item_id from spec_id for the API call
          const itemId = currentSpec.spec_id.startsWith('spec_')
            ? currentSpec.spec_id.substring(5)
            : currentSpec.spec_id
          loadSpecification(itemId, selectedProject)
        }
      }
    }
    socket.on('spec.tasks_progress', progressHandler)
    socket.on('spec.tasks_done', doneHandler)
    return () => {
      socket.off('spec.tasks_progress', progressHandler)
      socket.off('spec.tasks_done', doneHandler)
      socket.disconnect()
    }
  }, [currentSpec?.spec_id])

  return (
    <div className="h-full flex">
      {/* Left Side - Ideas in Definition */}
      <motion.div
        initial={{ x: -300, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="bg-black/20 backdrop-blur-md border-r border-white/10 flex flex-col flex-shrink-0"
        style={{ width: `${leftPaneWidth}px` }}
      >
        <div className="p-4 border-b border-white/10">
          <h2 className="text-lg font-semibold text-white mb-2">Ideas in Definition</h2>
          <div className="text-xs text-white/60 bg-white/10 px-2 py-1 rounded-full inline-block">
            {ideasInDefinition.length} items
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {ideasInDefinition.map((item, index) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className={clsx(
                'relative',
                openAssistantSelector === item.id ? 'z-20' : `z-${10 - index}`
              )}
            >
              <LiquidCard
                variant="feed"
                severity="info"
                urgency="medium"
                onClick={() => onFeedItemSelect(item.id)}
                className={clsx(
                  'cursor-pointer transition-all overflow-visible w-full',
                  selectedFeedItem === item.id && 'ring-2 ring-blue-500/50'
                )}
                style={{ overflow: 'visible' }}
              >
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center">
                    <span className="text-blue-400 text-sm">📝</span>
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <h4 className="font-medium text-white text-sm leading-tight">
                      {item.title}
                    </h4>
                    <p className="text-xs text-white/70 mt-1 line-clamp-2">
                      {item.summary}
                    </p>
                    <div className="flex items-center justify-between mt-3">
                      <div className="text-xs text-white/50">
                        {item.actor}
                      </div>
                      <div className="flex items-center space-x-2">
                        <AssistantSelector
                          onAssistantSelect={(assistant) => handleAssistantSelect(assistant, item)}
                          onToggle={(isOpen) => setOpenAssistantSelector(isOpen ? item.id : null)}
                          disabled={specLoading}
                          className="min-w-[180px]"
                        />
                        <div className="text-xs text-blue-400 bg-blue-500/20 px-2 py-1 rounded-full">
                          In Definition
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </LiquidCard>
            </motion.div>
          ))}

          {ideasInDefinition.length === 0 && (
            <div className="text-center py-8">
              <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-white/5 flex items-center justify-center">
                <span className="text-white/40 text-lg">📝</span>
              </div>
              <h3 className="text-sm font-medium text-white/80 mb-2">No ideas in definition</h3>
              <p className="text-xs text-white/60">
                Drag ideas from Think to start defining them
              </p>
            </div>
          )}
        </div>
      </motion.div>

      {/* Left Resize Handle */}
      <div
        className="w-1 bg-white/10 hover:bg-purple-500/50 cursor-col-resize transition-colors relative group"
        onMouseDown={() => setIsDraggingLeft(true)}
      >
        <div className="absolute inset-y-0 -left-1 -right-1 group-hover:bg-purple-500/20" />
      </div>

      {/* Center - Three-Tab Specification Editor */}
      <motion.div
        initial={{ x: 300, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: 'easeOut', delay: 0.1 }}
        className="flex-1 bg-black/10 backdrop-blur-sm flex flex-col min-w-0"
      >
        {currentSpec && (
          <>
            {/* Progress Bar */}
            <div className="h-1 bg-white/10 relative">
              <motion.div
                className="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-500 to-green-500"
                initial={{ width: 0 }}
                animate={{ width: `${calculateProgress(currentSpec)}%` }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
              />
            </div>

            {/* Header */}
            <div className="p-6 border-b border-white/10">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-2xl font-bold text-white mb-2">Specification</h1>
                  <p className="text-white/70 text-sm">
                    {calculateProgress(currentSpec)}% human reviewed
                  </p>
                </div>
                
                <div className="flex items-center space-x-3">
                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => setAiAssistantOpen(!aiAssistantOpen)}
                    className="cursor-pointer transition-transform"
                    title="Chat with AI Assistant"
                  >
                    <img 
                      src="./robot-assistant.png" 
                      alt="AI Assistant" 
                      className="h-32 w-auto object-contain"
                    />
                  </motion.button>
                  
                  <motion.button
                    whileHover={{ scale: currentSpec.completion_status.ready_to_freeze ? 1.05 : 1 }}
                    whileTap={{ scale: currentSpec.completion_status.ready_to_freeze ? 0.95 : 1 }}
                    onClick={freezeSpecification}
                    disabled={!currentSpec.completion_status.ready_to_freeze}
                    className={clsx(
                      'neon-btn transition-all',
                      !currentSpec.completion_status.ready_to_freeze && 'neon-btn--disabled'
                    )}
                  >
                    Freeze Spec
                  </motion.button>
                </div>
              </div>
            </div>

            {/* Tab Navigation */}
            <div className="flex border-b border-white/10">
              {(['requirements', 'design', 'tasks'] as const).map((tab) => {
                const artifact = currentSpec[tab]
                const badge = artifact?.status === 'ai_draft' ? '🟡' : 
                            artifact?.status === 'human_reviewed' ? '🟢' : 
                            artifact?.status === 'frozen' ? '🔒' : '⚪'
                
                return (
                  <motion.button
                    key={tab}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => setActiveTab(tab)}
                    className={clsx(
                      'flex-1 px-6 py-4 text-sm font-medium transition-all relative',
                      activeTab === tab
                        ? 'text-white bg-white/5 border-b-2 border-blue-500'
                        : 'text-white/70 hover:text-white hover:bg-white/5'
                    )}
                  >
                    <div className="flex items-center justify-center space-x-2">
                      <span className="capitalize">{tab}</span>
                      <span className="text-xs">{badge}</span>
                    </div>
                  </motion.button>
                )
              })}
            </div>

            {/* Tab Content */}
            <div className="flex-1 flex">
              <div className="flex-1 overflow-hidden">
                <SimpleSpecificationEditor
                  artifact={currentSpec[activeTab]}
                  artifactType={activeTab}
                  onUpdate={(content) => updateArtifact(activeTab, content)}
                  onMarkReviewed={(notes) => markAsHumanReviewed(activeTab, notes)}
                  loading={specLoading}
                  error={specError}
                  currentSpec={currentSpec}
                  onGenerateDesign={generateDesignDocument}
                  onGenerateTasks={generateTasksDocument}
                  streamingContent={tasksStreamingContent}
                  generating={tasksGenerating}
                />
              </div>
              
              {/* AI Assistant Panel */}
              <AnimatePresence>
                {aiAssistantOpen && (
                  <>
                    {/* Right Resize Handle */}
                    <div
                      className="w-1 bg-white/10 hover:bg-purple-500/50 cursor-col-resize transition-colors relative group"
                      onMouseDown={() => setIsDraggingRight(true)}
                    >
                      <div className="absolute inset-y-0 -left-1 -right-1 group-hover:bg-purple-500/20" />
                    </div>

                    <motion.div
                      initial={{ width: 0, opacity: 0 }}
                      animate={{ width: rightPaneWidth, opacity: 1 }}
                      exit={{ width: 0, opacity: 0 }}
                      transition={{ duration: 0.3, ease: 'easeOut' }}
                      className="bg-black/20 backdrop-blur-md flex-shrink-0"
                      style={{ width: `${rightPaneWidth}px` }}
                    >
                      <AIAssistantPanel
                        currentSpec={currentSpec}
                        activeTab={activeTab}
                        onClose={() => setAiAssistantOpen(false)}
                        onSuggestion={(content) => updateArtifact(activeTab, content)}
                      />
                    </motion.div>
                  </>
                )}
              </AnimatePresence>
            </div>
          </>
        )}

        {!currentSpec && !specLoading && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center text-white/60 p-8">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-white/5 flex items-center justify-center">
                <span className="text-white/40 text-2xl">📝</span>
              </div>
              <h3 className="text-lg font-medium mb-2">Select an idea to define</h3>
              <p className="text-sm">
                Choose an idea from the left to start creating its specification
              </p>
            </div>
          </div>
        )}

        {specLoading && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-white/10 flex items-center justify-center">
                <svg className="w-6 h-6 animate-spin text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </div>
              <p className="text-white/80">Loading specification...</p>
            </div>
          </div>
        )}
      </motion.div>

      {/* Spec Workflow Editor */}
      <AnimatePresence>
        {showProgressiveEditor && selectedFeedItemForSpec && selectedProject && (
          <SpecWorkflowEditor
            feedItem={selectedFeedItemForSpec}
            projectId={selectedProject}
            onComplete={closeProgressiveEditor}
            onClose={closeProgressiveEditor}
          />
        )}
      </AnimatePresence>

      {/* Kiro Workflow Manager */}
      <AnimatePresence>
        {showKiroWorkflow && kiroFeedItem && selectedProject && (
          <KiroWorkflowManager
            projectId={selectedProject}
            ideaContent={kiroFeedItem.summary || kiroFeedItem.title}
            feedItem={kiroFeedItem}
            onComplete={handleKiroWorkflowComplete}
            onClose={handleKiroWorkflowClose}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

interface SimpleSpecificationEditorProps {
  artifact?: SpecificationArtifact
  artifactType: 'requirements' | 'design' | 'tasks'
  onUpdate: (content: string) => void
  onMarkReviewed: (reviewNotes?: string) => void
  loading: boolean
  error: string | null
  currentSpec: SpecificationSet
  onGenerateDesign?: () => void
  onGenerateTasks?: () => void
  streamingContent?: string
  generating?: boolean
}

const SimpleSpecificationEditor: React.FC<SimpleSpecificationEditorProps> = ({
  artifact,
  artifactType,
  onUpdate,
  onMarkReviewed,
  loading,
  error,
  currentSpec,
  onGenerateDesign,
  onGenerateTasks,
  streamingContent = '',
  generating = false,
}) => {
  const [content, setContent] = useState(artifact?.content || '')
  const [reviewNotes, setReviewNotes] = useState('')
  const [showReviewDialog, setShowReviewDialog] = useState(false)

  useEffect(() => {
    const newContent = artifact?.content || ''
    console.log(`Setting ${artifactType} content:`, {
      length: newContent.length,
      preview: newContent.substring(0, 100),
      ending: newContent.substring(newContent.length - 100)
    })
    setContent(newContent)
  }, [artifact, artifactType])

  const handleContentChange = (newContent: string) => {
    setContent(newContent)
    // Debounced auto-save
    const timeoutId = setTimeout(() => {
      onUpdate(newContent)
    }, 1000)
    
    return () => clearTimeout(timeoutId)
  }

  const handleMarkReviewed = () => {
    onMarkReviewed(reviewNotes)
    setShowReviewDialog(false)
    setReviewNotes('')
  }

  const getBadgeInfo = () => {
    if (!artifact) return { icon: '⚪', text: 'Not Created', color: 'gray' }
    
    switch (artifact.status) {
      case 'ai_draft':
        return { icon: '🟡', text: 'AI Draft', color: 'yellow' }
      case 'human_reviewed':
        return { icon: '🟢', text: 'Human Reviewed', color: 'green' }
      case 'frozen':
        return { icon: '🔒', text: 'Frozen', color: 'blue' }
      default:
        return { icon: '⚪', text: 'Unknown', color: 'gray' }
    }
  }

  const badge = getBadgeInfo()

  const getWorkflowStep = (spec: SpecificationSet, currentArtifact: string) => {
    if (!spec.requirements) return 'Step 1 of 3'
    if (!spec.design) return 'Step 2 of 3'
    if (!spec.tasks) return 'Step 3 of 3'
    return 'Complete'
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <h3 className="text-lg font-semibold text-white capitalize">
            {artifactType}.md
          </h3>
          <div className={clsx(
            'px-3 py-1 rounded-full text-xs font-medium flex items-center space-x-1',
            badge.color === 'yellow' && 'bg-yellow-500/20 text-yellow-400',
            badge.color === 'green' && 'bg-green-500/20 text-green-400',
            badge.color === 'blue' && 'bg-blue-500/20 text-blue-400',
            badge.color === 'gray' && 'bg-gray-500/20 text-gray-400'
          )}>
            <span>{badge.icon}</span>
            <span>{badge.text}</span>
          </div>
        </div>

        {artifact && artifact.status === 'ai_draft' && (
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setShowReviewDialog(true)}
            className="px-4 py-2 bg-green-500/20 text-green-400 rounded-lg border border-green-500/30 hover:bg-green-500/30 transition-all text-sm"
          >
            Mark as Reviewed
          </motion.button>
        )}
      </div>

      {/* Content Editor */}
      <div className="flex-1 p-4">
        {artifact ? (
          artifactType === 'tasks' ? (
            <TasksViewer
              content={content}
              onChange={handleContentChange}
              disabled={artifact.status === 'frozen'}
              streamingContent={streamingContent}
              generating={generating}
            />
          ) : (
            <textarea
              value={content}
              onChange={(e) => handleContentChange(e.target.value)}
              placeholder={`Enter ${artifactType} content...`}
              className="w-full h-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none font-mono text-sm"
              disabled={artifact.status === 'frozen'}
            />
          )
        ) : (
          <div className="h-full flex items-center justify-center">
            <div className="text-center text-white/60">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-white/5 flex items-center justify-center">
                <img 
                  src="orb.png" 
                  alt="Orb" 
                  className="w-10 h-10 object-contain opacity-60"
                />
              </div>
              <h4 className="text-sm font-medium mb-2">No {artifactType} yet</h4>
              <p className="text-xs">
                This will be generated by the Define Agent
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Workflow Progress and Actions */}
      {artifact && (
        <div className="p-4 border-t border-white/10">
          {/* Workflow Progress Indicator */}
          <div className="mb-4">
            <div className="flex items-center justify-between text-xs text-white/60 mb-2">
              <span>Workflow Progress</span>
              <span>{getWorkflowStep(currentSpec, artifactType)}</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className={clsx(
                'w-3 h-3 rounded-full',
                currentSpec.requirements?.status === 'human_reviewed' || currentSpec.requirements?.status === 'frozen'
                  ? 'bg-green-500' : currentSpec.requirements ? 'bg-yellow-500' : 'bg-gray-500'
              )} />
              <div className="flex-1 h-0.5 bg-white/10">
                <div className={clsx(
                  'h-full transition-all duration-500',
                  currentSpec.design ? 'bg-blue-500' : 'bg-transparent'
                )} />
              </div>
              <div className={clsx(
                'w-3 h-3 rounded-full',
                currentSpec.design?.status === 'human_reviewed' || currentSpec.design?.status === 'frozen'
                  ? 'bg-green-500' : currentSpec.design ? 'bg-yellow-500' : 'bg-gray-500'
              )} />
              <div className="flex-1 h-0.5 bg-white/10">
                <div className={clsx(
                  'h-full transition-all duration-500',
                  currentSpec.tasks ? 'bg-purple-500' : 'bg-transparent'
                )} />
              </div>
              <div className={clsx(
                'w-3 h-3 rounded-full',
                currentSpec.tasks?.status === 'human_reviewed' || currentSpec.tasks?.status === 'frozen'
                  ? 'bg-green-500' : currentSpec.tasks ? 'bg-yellow-500' : 'bg-gray-500'
              )} />
            </div>
            <div className="flex justify-between text-xs text-white/40 mt-1">
              <span>Requirements</span>
              <span>Design</span>
              <span>Tasks</span>
            </div>
          </div>

          {/* Workflow Action Buttons */}
          {artifact.status === 'human_reviewed' && (
            <>
              {artifactType === 'requirements' && !currentSpec.design && onGenerateDesign && (
                <div className="space-y-3">
                  <div className="text-center">
                    <p className="text-sm text-white/70 mb-2">
                      **Do the requirements look good? If so, we can move on to the design.**
                    </p>
                  </div>
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={onGenerateDesign}
                    disabled={loading}
                    className="w-full px-4 py-3 bg-blue-500/20 text-blue-400 rounded-lg border border-blue-500/30 hover:bg-blue-500/30 transition-all text-sm font-medium flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? (
                      <>
                        <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        <span>Generating Design...</span>
                      </>
                    ) : (
                      <>
                        <span>✨</span>
                        <span>Generate Design Document</span>
                      </>
                    )}
                  </motion.button>
                </div>
              )}
              
              {artifactType === 'design' && !currentSpec.tasks && onGenerateTasks && (
                <div className="space-y-3">
                  <div className="text-center">
                    <p className="text-sm text-white/70 mb-2">
                      **Does the design look good? If so, we can move on to the implementation tasks.**
                    </p>
                  </div>
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={onGenerateTasks}
                    disabled={loading}
                    className="w-full px-4 py-3 bg-purple-500/20 text-purple-400 rounded-lg border border-purple-500/30 hover:bg-purple-500/30 transition-all text-sm font-medium flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? (
                      <>
                        <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        <span>Generating Tasks...</span>
                      </>
                    ) : (
                      <>
                        <span>📋</span>
                        <span>Generate Implementation Tasks</span>
                      </>
                    )}
                  </motion.button>
                </div>
              )}

              {artifactType === 'tasks' && currentSpec.tasks?.status === 'human_reviewed' && (
                <div className="space-y-3">
                  <div className="text-center">
                    <p className="text-sm text-white/70 mb-2">
                      **Do the tasks look good? You can now freeze the specification to move to the Plan stage.**
                    </p>
                  </div>
                  <div className="text-xs text-white/50 text-center">
                    Use the "Freeze Spec" button in the header to complete the specification.
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Review Dialog */}
      <AnimatePresence>
        {showReviewDialog && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50"
            onClick={() => setShowReviewDialog(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-black/80 backdrop-blur-md border border-white/20 rounded-xl p-6 max-w-md w-full mx-4"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-lg font-semibold text-white mb-4">
                Mark as Human Reviewed
              </h3>
              <p className="text-white/70 text-sm mb-4">
                Add any review notes or comments about this {artifactType} specification.
              </p>
              <textarea
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="Optional review notes..."
                className="w-full h-24 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none text-sm mb-4"
              />
              <div className="flex space-x-3">
                <button
                  onClick={() => setShowReviewDialog(false)}
                  className="flex-1 px-4 py-2 bg-white/10 text-white rounded-lg hover:bg-white/20 transition-all"
                >
                  Cancel
                </button>
                <button
                  onClick={handleMarkReviewed}
                  className="flex-1 px-4 py-2 bg-green-500/20 text-green-400 rounded-lg border border-green-500/30 hover:bg-green-500/30 transition-all"
                >
                  Mark Reviewed
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

interface AIAssistantPanelProps {
  currentSpec: SpecificationSet
  activeTab: 'requirements' | 'design' | 'tasks'
  onClose: () => void
  onSuggestion: (content: string) => void
}

const AIAssistantPanel: React.FC<AIAssistantPanelProps> = ({
  currentSpec,
  activeTab,
  onClose,
  onSuggestion,
}) => {
  const [query, setQuery] = useState('')
  const [response, setResponse] = useState('')
  const [loading, setLoading] = useState(false)

  const handleAskAI = async () => {
    if (!query.trim()) return

    setLoading(true)
    try {
      // This would call the AI assistant API
      const aiResponse = await missionControlApi.askAIAssistant({
        query,
        context: {
          spec_id: currentSpec.spec_id,
          artifact_type: activeTab,
          current_content: currentSpec[activeTab]?.content || ''
        }
      })
      setResponse(aiResponse.response)
    } catch (error) {
      console.error('AI assistant error:', error)
      setResponse('Sorry, I encountered an error. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-white/10 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <img 
            src="./robot-assistant.png" 
            alt="AI Assistant" 
            className="h-10 w-auto object-contain"
          />
          <h3 className="text-lg font-semibold text-white">AI Assistant</h3>
        </div>
        <button
          onClick={onClose}
          className="text-white/60 hover:text-white transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 p-4 space-y-4">
        <div>
          <label className="block text-sm font-medium text-white/80 mb-2">
            Ask about {activeTab}
          </label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={`How can I improve the ${activeTab} specification?`}
            className="w-full h-24 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-purple-500/50 resize-none text-sm"
          />
          <button
            onClick={handleAskAI}
            disabled={loading || !query.trim()}
            className="mt-2 w-full px-4 py-2 bg-purple-500/20 text-purple-400 rounded-lg border border-purple-500/30 hover:bg-purple-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Thinking...' : 'Ask AI'}
          </button>
        </div>

        {response && (
          <div className="space-y-2">
            <label className="block text-sm font-medium text-white/80">
              AI Response
            </label>
            <div className="bg-white/5 border border-white/10 rounded-lg p-3 text-white/90 text-sm">
              {response}
            </div>
            <button
              onClick={() => onSuggestion(response)}
              className="w-full px-4 py-2 bg-blue-500/20 text-blue-400 rounded-lg border border-blue-500/30 hover:bg-blue-500/30 transition-all text-sm"
            >
              Apply Suggestion
            </button>
          </div>
        )}
      </div>
    </div>
  )
}



interface TasksViewerProps {
  content: string
  onChange: (content: string) => void
  disabled: boolean
  streamingContent?: string
  generating?: boolean
}

const TasksViewer: React.FC<TasksViewerProps> = ({ content, onChange, disabled, streamingContent = '' }) => {
  const [tasks, setTasks] = useState<Array<{ id: string; text: string; completed: boolean; level: number }>>([])
  const [editMode, setEditMode] = useState(false)

  useEffect(() => {
    // Parse markdown tasks from content
    const parsedTasks = parseTasksFromMarkdown(content)
    setTasks(parsedTasks)
  }, [content])

  const parseTasksFromMarkdown = (markdown: string) => {
    const lines = markdown.split('\n')
    const tasks: Array<{ id: string; text: string; completed: boolean; level: number }> = []
    
    const taskRegex = /^(\s*)[-*•–]\s*(?:\[([ xX])\]\s*)?(.+)/
    lines.forEach((line, index) => {
      const taskMatch = line.match(taskRegex)
      if (taskMatch) {
        const [, indent, status, text] = taskMatch
        const level = Math.floor(indent.length / 2)
        tasks.push({
          id: `task-${index}`,
          text: text.trim(),
          completed: status?.toLowerCase() === 'x',
          level
        })
      }
    })
    
    return tasks
  }

  const toggleTask = (taskId: string) => {
    if (disabled) return
    
    const updatedTasks = tasks.map(task => 
      task.id === taskId ? { ...task, completed: !task.completed } : task
    )
    setTasks(updatedTasks)
    
    // Update the markdown content
    const updatedMarkdown = generateMarkdownFromTasks(updatedTasks, content)
    onChange(updatedMarkdown)
  }

  const generateMarkdownFromTasks = (tasks: Array<{ id: string; text: string; completed: boolean; level: number }>, originalContent: string) => {
    const rebuilt = tasks.map(t => {
      const indent = '  '.repeat(t.level)
      return `${indent}- [${t.completed ? 'x' : ' '}] ${t.text}`
    }).join('\n')
    return rebuilt
  }

  const startTask = (task: { id: string; text: string; completed: boolean; level: number }) => {
    // This would integrate with Kiro's task execution system
    console.log('Starting task:', task.text)
    // In a real implementation, this would:
    // 1. Open Kiro with the task context
    // 2. Set up the workspace for the task
    // 3. Provide the task instructions to Kiro
  }

  if (editMode) {
    return (
      <div className="h-full flex flex-col">
        <div className="flex justify-between items-center mb-4">
          <h4 className="text-sm font-medium text-white">Edit Tasks (Markdown)</h4>
          <button
            onClick={() => setEditMode(false)}
            className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded text-xs hover:bg-blue-500/30 transition-all"
          >
            View Tasks
          </button>
        </div>
        <textarea
          value={content}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Enter tasks in markdown format..."
          className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none font-mono text-sm"
          disabled={disabled}
        />
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <h4 className="text-sm font-medium text-white">Implementation Tasks</h4>
        <button
          onClick={() => setEditMode(true)}
          className="px-3 py-1 bg-white/10 text-white/70 rounded text-xs hover:bg-white/20 transition-all"
        >
          Edit Markdown
        </button>
      </div>
      
      <div className="flex-1 overflow-y-auto space-y-2">
        {tasks.map((task) => (
          <motion.div
            key={task.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={clsx(
              'flex items-start space-x-3 p-3 rounded-lg border transition-all',
              task.level === 0 ? 'bg-white/5 border-white/10' : 'bg-white/2 border-white/5 ml-6',
              task.completed && 'opacity-60'
            )}
          >
            <button
              onClick={() => toggleTask(task.id)}
              disabled={disabled}
              className={clsx(
                'flex-shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center transition-all mt-0.5',
                task.completed
                  ? 'bg-green-500 border-green-500 text-white'
                  : 'border-white/30 hover:border-white/50',
                disabled && 'cursor-not-allowed'
              )}
            >
              {task.completed && (
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              )}
            </button>
            
            <div className="flex-1 min-w-0">
              <p className={clsx(
                'text-sm text-white',
                task.completed && 'line-through text-white/60'
              )}>
                {task.text}
              </p>
            </div>
            
            {!task.completed && !disabled && (
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => startTask(task)}
                className="flex-shrink-0 px-3 py-1 bg-blue-500/20 text-blue-400 rounded text-xs border border-blue-500/30 hover:bg-blue-500/30 transition-all"
              >
                Start Task
              </motion.button>
            )}
          </motion.div>
        ))}
        
        {tasks.length === 0 && (
          <div className="text-center py-8 text-white/60">
            <p className="text-sm">No tasks found in the content.</p>
            <p className="text-xs mt-1">Tasks should be in markdown format: - [ ] Task description</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default DefineStage