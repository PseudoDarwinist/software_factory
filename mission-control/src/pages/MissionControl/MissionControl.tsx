/**
 * Mission Control Page - Main page component
 * 
 * This is the main page component that orchestrates the entire Mission Control
 * experience. It connects all the layout components with the state management
 * and API services.
 * 
 * Why this page exists:
 * - Orchestrates the entire Mission Control experience
 * - Connects UI components with state management
 * - Handles real-time updates and data synchronization
 * - Manages the overall application lifecycle
 * 
 * For AI agents: This is the main entry point for Mission Control.
 * All the major functionality is coordinated from here.
 */

import React, { useEffect, useRef, useCallback } from 'react'
import { DndProvider } from 'react-dnd'
import { HTML5Backend } from 'react-dnd-html5-backend'
import { motion, AnimatePresence } from 'framer-motion'
import { MissionControlLayout } from '@/components/layout/MissionControlLayout'
import { 
  useMissionControlStore, 
  useActions, 
  useUIState, 
  useLoadingState, 
  useErrorState 
} from '@/stores/missionControlStore'
import { missionControlApi } from '@/services/api/missionControlApi'
import { tokens } from '@/styles/tokens'
import type { RealtimeEvent } from '@/types'
import type { Socket } from 'socket.io-client'

export const MissionControl: React.FC = () => {
  const websocketRef = useRef<Socket | null>(null)
  const actions = useActions()
  const ui = useUIState()
  const loading = useLoadingState()
  const errors = useErrorState()
  
  // Get current state
  const { projects, feedItems, conversation } = useMissionControlStore()

  // Initialize data on mount
  useEffect(() => {
    loadInitialData()
    setupRealtimeUpdates()
    
    return () => {
      // Cleanup Socket.IO on unmount
      if (websocketRef.current) {
        websocketRef.current.disconnect()
      }
    }
  }, [])

  // Auto-refresh data periodically
  useEffect(() => {
    const interval = setInterval(() => {
      if (!loading.projects) {
        loadProjects()
      }
      if (!loading.feed) {
        loadFeedItems()
      }
    }, 30000) // Refresh every 30 seconds

    return () => clearInterval(interval)
  }, [loading.projects, loading.feed])

  // Load conversation when feed item is selected
  useEffect(() => {
    if (ui.selectedFeedItem) {
      loadConversation(ui.selectedFeedItem)
    } else {
      actions.setConversation(null)
    }
  }, [ui.selectedFeedItem])

  // Load initial data
  const loadInitialData = async () => {
    await Promise.all([
      loadProjects(),
      loadFeedItems(),
    ])
  }

  // Load projects
  const loadProjects = async () => {
    try {
      actions.setLoading('projects', true)
      actions.setError('projects', null)
      
      const projectsData = await missionControlApi.getProjects()
      actions.setProjects(projectsData)
    } catch (error) {
      actions.setError('projects', error instanceof Error ? error.message : 'Failed to load projects')
    } finally {
      actions.setLoading('projects', false)
    }
  }

  // Load feed items
  const loadFeedItems = async (projectId?: string) => {
    try {
      actions.setLoading('feed', true)
      actions.setError('feed', null)
      
      const feedData = await missionControlApi.getFeedItems({ projectId })
      actions.setFeedItems(feedData.items)
    } catch (error) {
      actions.setError('feed', error instanceof Error ? error.message : 'Failed to load feed items')
    } finally {
      actions.setLoading('feed', false)
    }
  }

  // Load conversation
  const loadConversation = async (feedItemId: string) => {
    try {
      actions.setLoading('conversation', true)
      actions.setError('conversation', null)
      
      const conversationData = await missionControlApi.getConversation(feedItemId)
      actions.setConversation(conversationData)
    } catch (error) {
      actions.setError('conversation', error instanceof Error ? error.message : 'Failed to load conversation')
    } finally {
      actions.setLoading('conversation', false)
    }
  }

  // Setup real-time updates
  const setupRealtimeUpdates = () => {
    try {
      websocketRef.current = missionControlApi.createSocketConnection(handleRealtimeEvent)
    } catch (error) {
      console.error('Failed to setup WebSocket connection:', error)
    }
  }

  // Handle real-time events
  const handleRealtimeEvent = useCallback((event: RealtimeEvent) => {
    switch (event.type) {
      case 'feed.update':
        // Update specific feed item
        if (event.payload.feedItemId) {
          actions.updateFeedItem(event.payload.feedItemId, event.payload.fields)
        }
        break
        
      case 'conversation.update':
        // Refresh conversation if it's currently open
        if (ui.selectedFeedItem && event.payload.feedItemId === ui.selectedFeedItem) {
          loadConversation(ui.selectedFeedItem)
        }
        break
        
      case 'project.update':
        // Update specific project
        if (event.payload.projectId) {
          actions.updateProject(event.payload.projectId, event.payload.fields)
        }
        break
        
      case 'system.notification':
        // Add system notification
        actions.addNotification(event.payload)
        break
        
      case 'stage.moved':
        // Refresh feed items when stage moves happen
        loadFeedItems(ui.selectedProject || undefined)
        break
        
      case 'feed.new':
        // Refresh feed items when new items arrive
        loadFeedItems(ui.selectedProject || undefined)
        break
        
      default:
        console.log('Unhandled real-time event:', event)
    }
  }, [ui.selectedFeedItem, actions])

  // Event handlers
  const handleProjectSelect = useCallback((projectId: string | null) => {
    actions.setSelectedProject(projectId)
    
    // Clear current feed item selection
    actions.setSelectedFeedItem(null)
    
    // Load feed items for selected project
    loadFeedItems(projectId || undefined)
  }, [actions])

  const handleFeedItemSelect = useCallback((feedItemId: string | null) => {
    actions.setSelectedFeedItem(feedItemId)
    
    // Mark as read
    if (feedItemId) {
      missionControlApi.markFeedItemRead(feedItemId).catch(console.error)
    }
  }, [actions])

  const handleStageChange = useCallback((stage: typeof ui.activeStage) => {
    actions.setActiveStage(stage)
  }, [actions])

  const handlePromptSubmit = useCallback(async (prompt: string) => {
    if (!ui.selectedFeedItem) return
    
    try {
      actions.setLoading('action', true)
      actions.setError('action', null)
      
      await missionControlApi.submitPrompt(ui.selectedFeedItem, prompt)
      
      // Refresh conversation to show response
      await loadConversation(ui.selectedFeedItem)
    } catch (error) {
      actions.setError('action', error instanceof Error ? error.message : 'Failed to submit prompt')
    } finally {
      actions.setLoading('action', false)
    }
  }, [ui.selectedFeedItem, actions])

  const handleFeedItemAction = useCallback(async (feedItemId: string, action: string) => {
    try {
      actions.setLoading('action', true)
      actions.setError('action', null)
      
      await missionControlApi.performFeedItemAction(feedItemId, action)
      
      // Refresh feed items
      await loadFeedItems(ui.selectedProject || undefined)
    } catch (error) {
      actions.setError('action', error instanceof Error ? error.message : 'Failed to perform action')
    } finally {
      actions.setLoading('action', false)
    }
  }, [ui.selectedProject, actions])

  const handleItemDrop = useCallback(async (itemId: string, fromStage: typeof ui.activeStage, toStage: typeof ui.activeStage) => {
    console.log('[MissionControl] handleItemDrop called', { itemId, fromStage, toStage, selectedProject: ui.selectedProject })
    // Determine the project context. Prefer the currently selected project, but
    // fall back to the project associated with the feed item itself. This allows
    // drag-and-drop to work even when the user has not explicitly selected a
    // project in the sidebar.
    const projectId = ui.selectedProject || feedItems.find((f) => f.id === itemId)?.projectId
    console.log('[MissionControl] Resolved projectId', projectId)
    if (!projectId) {
      actions.setError('action', 'Unable to determine project for this item')
      return
    }

    try {
      actions.setLoading('action', true)
      actions.setError('action', null)

      // Optimistically mark this feed item as being in the target stage so the
      // DefineStage sidebar shows it immediately.
      actions.updateFeedItem(itemId, { metadata: { ...(feedItems.find(f => f.id === itemId)?.metadata || {}), stage: toStage } })

      // Optimistically switch the UI stage so users get immediate feedback.
      if (toStage === 'define') {
        actions.setActiveStage('define')
        actions.setSelectedFeedItem(itemId)
      }

      // Attempt the server mutation. If it fails, the error toast will inform the
      // user and the optimistic UI can be rolled back manually if desired.
      const result = await missionControlApi.moveItemToStage(itemId, toStage, fromStage, projectId)

      // If the backend returns a brief in response, you might choose to do
      // something with it here (e.g., store it in state). This is left as a TODO
      // because the existing UI does not yet surface that data.

      // Refresh feed items to reflect the change. Use the resolved projectId so
      // we stay in the same project context.
      await loadFeedItems(projectId)
    } catch (error) {
      actions.setError('action', error instanceof Error ? error.message : 'Failed to move item')
    } finally {
      actions.setLoading('action', false)
    }
  }, [ui.selectedProject, feedItems, actions])

  return (
    <DndProvider backend={HTML5Backend}>
      <div className="min-h-screen bg-black text-white">
        {/* Main Mission Control Layout */}
        <MissionControlLayout
          projects={projects}
          feedItems={feedItems}
          conversation={conversation}
          selectedProject={ui.selectedProject}
          selectedFeedItem={ui.selectedFeedItem}
          activeStage={ui.activeStage}
          onProjectSelect={handleProjectSelect}
          onFeedItemSelect={handleFeedItemSelect}
          onStageChange={handleStageChange}
          onPromptSubmit={handlePromptSubmit}
          onFeedItemAction={handleFeedItemAction}
          onItemDrop={handleItemDrop}
          loading={loading}
          errors={errors}
        />

        {/* Global Error Toast */}
        <AnimatePresence>
          {(errors.projects || errors.feed || errors.conversation || errors.action) && (
            <motion.div
              initial={{ opacity: 0, y: 50 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 50 }}
              className="fixed bottom-4 right-4 bg-red-500/20 border border-red-500/50 rounded-lg p-4 backdrop-blur-sm z-50"
            >
              <div className="flex items-center space-x-2">
                <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <div>
                  <h4 className="font-medium text-red-300">Error</h4>
                  <p className="text-sm text-red-200">
                    {errors.projects || errors.feed || errors.conversation || errors.action}
                  </p>
                </div>
                <button
                  onClick={() => {
                    actions.setError('projects', null)
                    actions.setError('feed', null)
                    actions.setError('conversation', null)
                    actions.setError('action', null)
                  }}
                  className="text-red-400 hover:text-red-300"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Loading Overlay */}
        <AnimatePresence>
          {loading.action && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 flex items-center justify-center"
            >
              <div className="bg-white/10 rounded-lg p-6 flex items-center space-x-3">
                <svg className="w-6 h-6 animate-spin text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span className="text-white">Processing...</span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </DndProvider>
  )
}

export default MissionControl