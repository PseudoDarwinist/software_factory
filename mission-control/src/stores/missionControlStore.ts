/**
 * Mission Control Store - Central state management
 * 
 * This store manages all the state for Mission Control using Zustand.
 * It provides a clean, predictable state management pattern that's
 * easy for AI agents to understand and modify.
 * 
 * Why this store exists:
 * - Centralized state management for Mission Control
 * - Predictable state updates with clear actions
 * - Easy to test and debug
 * - Type-safe state management
 * 
 * For AI agents: This is the main state store for Mission Control.
 * All component state should be managed through this store.
 */

import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type { 
  ProjectSummary, 
  FeedItem, 
  ConversationPayload, 
  SDLCStage, 
  UIState, 
  LoadingState, 
  ErrorState,
  SystemNotification
} from '@/types'

interface NotificationPrefs {
  toastsEnabled: boolean
  browserNotifications: boolean
  soundEnabled: boolean
  showSuccess: boolean
  showWarnings: boolean
  showErrors: boolean
}

interface MissionControlState {
  // Data
  projects: ProjectSummary[]
  feedItems: FeedItem[]
  conversation: ConversationPayload | null
  
  // UI State
  ui: UIState
  loading: LoadingState
  errors: ErrorState
  notifications: SystemNotification[]
  notificationPrefs: NotificationPrefs
  
  // Actions
  actions: {
    // Project actions
    setProjects: (projects: ProjectSummary[]) => void
    updateProject: (projectId: string, updates: Partial<ProjectSummary>) => void
    
    // Feed actions
    setFeedItems: (items: FeedItem[]) => void
    updateFeedItem: (itemId: string, updates: Partial<FeedItem>) => void
    removeFeedItem: (itemId: string) => void
    markFeedItemRead: (itemId: string) => void
    
    // Conversation actions
    setConversation: (conversation: ConversationPayload | null) => void
    
    // UI actions
    setSelectedProject: (projectId: string | null) => void
    setSelectedFeedItem: (itemId: string | null) => void
    setActiveStage: (stage: SDLCStage) => void
    setSidebarCollapsed: (collapsed: boolean) => void
    setTheme: (theme: 'dark' | 'light') => void
    
    // Loading actions
    setLoading: (key: keyof LoadingState, loading: boolean) => void
    
    // Error actions
    setError: (key: keyof ErrorState, error: string | null) => void
    
    // Notification actions
    addNotification: (notification: SystemNotification) => void
    removeNotification: (notificationId: string) => void
    clearNotifications: () => void

    // Notification preference actions
    setNotificationPrefs: (prefs: Partial<NotificationPrefs>) => void
    enableBrowserNotifications: () => Promise<void>
  }
}

const defaultPrefs: NotificationPrefs = {
  toastsEnabled: true,
  browserNotifications: false,
  soundEnabled: false,
  showSuccess: true,
  showWarnings: true,
  showErrors: true,
}

export const useMissionControlStore = create<MissionControlState>()(
  devtools(
    (set, get) => ({
      // Initial state
      projects: [],
      feedItems: [],
      conversation: null,
      
      ui: {
        sidebarCollapsed: false,
        selectedProject: null,
        selectedFeedItem: null,
        activeStage: 'think',
        theme: 'dark',
        notifications: [],
      },
      
      loading: {
        projects: false,
        feed: false,
        conversation: false,
        action: false,
      },
      
      errors: {
        projects: null,
        feed: null,
        conversation: null,
        action: null,
      },
      
      notifications: [],
      notificationPrefs: defaultPrefs,
      
      actions: {
        // Project actions
        setProjects: (projects) => set(() => ({
          projects
        })),
        
        updateProject: (projectId, updates) => set((state) => ({
          projects: state.projects.map(p => 
            p.id === projectId ? { ...p, ...updates } : p
          )
        })),
        
        // Feed actions
        setFeedItems: (items) => set(() => ({
          feedItems: items
        })),
        
        updateFeedItem: (itemId, updates) => set((state) => ({
          feedItems: state.feedItems.map(item => 
            item.id === itemId ? { ...item, ...updates } : item
          )
        })),
        
        removeFeedItem: (itemId) => set((state) => ({
          feedItems: state.feedItems.filter(i => i.id !== itemId)
        })),
        
        markFeedItemRead: (itemId) => set((state) => {
          const updatedFeedItems = state.feedItems.map(item =>
            item.id === itemId ? { ...item, unread: false } : item
          )
          
          const item = state.feedItems.find(i => i.id === itemId)
          const updatedProjects = item ? state.projects.map(project =>
            project.id === item.projectId && project.unreadCount > 0
              ? { ...project, unreadCount: project.unreadCount - 1 }
              : project
          ) : state.projects
          
          return {
            feedItems: updatedFeedItems,
            projects: updatedProjects
          }
        }),
        
        // Conversation actions
        setConversation: (conversation) => set(() => ({
          conversation
        })),
        
        // UI actions
        setSelectedProject: (projectId) => set((state) => ({
          ui: { ...state.ui, selectedProject: projectId }
        })),
        
        setSelectedFeedItem: (itemId) => set((state) => {
          const item = itemId ? state.feedItems.find(i => i.id === itemId) : null
          
          let updates: any = {
            ui: { ...state.ui, selectedFeedItem: itemId }
          }
          
          // Mark as read when selected
          if (item && item.unread) {
            updates.feedItems = state.feedItems.map(feedItem =>
              feedItem.id === itemId ? { ...feedItem, unread: false } : feedItem
            )
            
            updates.projects = state.projects.map(project =>
              project.id === item.projectId && project.unreadCount > 0
                ? { ...project, unreadCount: project.unreadCount - 1 }
                : project
            )
          }
          
          return updates
        }),
        
        setActiveStage: (stage) => set((state) => ({
          ui: { ...state.ui, activeStage: stage }
        })),
        
        setSidebarCollapsed: (collapsed) => set((state) => ({
          ui: { ...state.ui, sidebarCollapsed: collapsed }
        })),
        
        setTheme: (theme) => set((state) => ({
          ui: { ...state.ui, theme }
        })),
        
        // Loading actions
        setLoading: (key, loading) => set((state) => ({
          loading: { ...state.loading, [key]: loading }
        })),
        
        // Error actions
        setError: (key, error) => set((state) => ({
          errors: { ...state.errors, [key]: error }
        })),
        
        // Notification actions
        addNotification: (notification) => set((state) => ({
          notifications: [...state.notifications, notification]
        })),
        
        removeNotification: (notificationId) => set((state) => ({
          notifications: state.notifications.filter(n => n.id !== notificationId)
        })),
        
        clearNotifications: () => set(() => ({
          notifications: []
        })),

        // Notification preferences
        setNotificationPrefs: (prefs) => set((state) => ({
          notificationPrefs: { ...state.notificationPrefs, ...prefs }
        })),

        enableBrowserNotifications: async () => {
          try {
            if ('Notification' in window) {
              const permission = await Notification.requestPermission()
              if (permission === 'granted') {
                set((state) => ({ notificationPrefs: { ...state.notificationPrefs, browserNotifications: true } }))
              }
            }
          } catch {}
        },
      },
    }),
    {
      name: 'mission-control-store',
    }
  )
)

// Selectors for commonly used state
export const useProjects = () => useMissionControlStore(state => state.projects)
export const useFeedItems = () => useMissionControlStore(state => state.feedItems)
export const useConversation = () => useMissionControlStore(state => state.conversation)
export const useUIState = () => useMissionControlStore(state => state.ui)
export const useLoadingState = () => useMissionControlStore(state => state.loading)
export const useErrorState = () => useMissionControlStore(state => state.errors)
export const useNotifications = () => useMissionControlStore(state => state.notifications)
export const useActions = () => useMissionControlStore(state => state.actions)
export const useNotificationPrefs = () => useMissionControlStore(state => state.notificationPrefs)

// Computed selectors
export const useSelectedProject = () => useMissionControlStore(state => 
  state.projects.find(p => p.id === state.ui.selectedProject) || null
)

export const useSelectedFeedItem = () => useMissionControlStore(state => 
  state.feedItems.find(i => i.id === state.ui.selectedFeedItem) || null
)

export const useFilteredFeedItems = (projectId?: string | null) => useMissionControlStore(state => 
  projectId 
    ? state.feedItems.filter(item => item.projectId === projectId)
    : state.feedItems
)

export const useUnreadCount = (projectId?: string) => useMissionControlStore(state => 
  projectId 
    ? state.feedItems.filter(item => item.projectId === projectId && item.unread).length
    : state.feedItems.filter(item => item.unread).length
)

export const useProjectHealth = (projectId: string) => useMissionControlStore(state => 
  state.projects.find(p => p.id === projectId)?.health || 'green'
)