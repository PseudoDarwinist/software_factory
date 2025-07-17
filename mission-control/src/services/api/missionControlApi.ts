/**
 * Mission Control API Service
 * 
 * This service handles all API communication for Mission Control.
 * It provides type-safe, clean interfaces for all backend operations.
 * 
 * Why this service exists:
 * - Centralized API logic with consistent error handling
 * - Type-safe API calls matching the backend contracts
 * - Easy to mock for testing
 * - Clear separation between API and business logic
 * 
 * For AI agents: This is the main API service for Mission Control.
 * All backend communication should go through these methods.
 */

import axios, { AxiosInstance, AxiosError } from 'axios'
import { io, Socket } from 'socket.io-client'
import type { 
  ApiResponse, 
  PaginatedResponse, 
  ProjectSummary, 
  FeedItem, 
  ConversationPayload,
  SDLCStage,
  Command
} from '@/types'

class MissionControlApi {
  private client: AxiosInstance
  private baseURL: string

  constructor(baseURL: string = 'http://localhost:5001/api') {
    this.baseURL = baseURL
    this.client = axios.create({
      baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
    // Request interceptor for auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('auth_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Handle unauthorized - redirect to login
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )
  }

  // Project endpoints
  async getProjects(): Promise<ProjectSummary[]> {
    try {
      const response = await this.client.get<ApiResponse<ProjectSummary[]>>('/projects')
      return response.data.data || []
    } catch (error) {
      console.error('Failed to fetch projects:', error)
      throw new Error('Failed to fetch projects')
    }
  }

  async getProject(projectId: string): Promise<ProjectSummary | null> {
    try {
      const response = await this.client.get<ApiResponse<ProjectSummary>>(`/projects/${projectId}`)
      return response.data.data || null
    } catch (error) {
      console.error('Failed to fetch project:', error)
      throw new Error('Failed to fetch project')
    }
  }

  async updateProject(projectId: string, updates: Partial<ProjectSummary>): Promise<ProjectSummary> {
    try {
      const response = await this.client.patch<ApiResponse<ProjectSummary>>(`/projects/${projectId}`, updates)
      return response.data.data!
    } catch (error) {
      console.error('Failed to update project:', error)
      throw new Error('Failed to update project')
    }
  }

  // Feed endpoints
  async getFeedItems(params: {
    projectId?: string
    cursor?: string
    limit?: number
    severity?: 'info' | 'amber' | 'red'
    unread?: boolean
  } = {}): Promise<PaginatedResponse<FeedItem>> {
    try {
      const response = await this.client.get<ApiResponse<PaginatedResponse<FeedItem>>>('/feed', {
        params: {
          ...params,
          limit: params.limit || 20,
        },
      })
      return response.data.data!
    } catch (error) {
      console.error('Failed to fetch feed items:', error)
      throw new Error('Failed to fetch feed items')
    }
  }

  async getFeedItem(feedItemId: string): Promise<FeedItem | null> {
    try {
      const response = await this.client.get<ApiResponse<FeedItem>>(`/feed/${feedItemId}`)
      return response.data.data || null
    } catch (error) {
      console.error('Failed to fetch feed item:', error)
      throw new Error('Failed to fetch feed item')
    }
  }

  async markFeedItemRead(feedItemId: string): Promise<void> {
    try {
      await this.client.post(`/feed/${feedItemId}/mark-read`)
    } catch (error) {
      console.error('Failed to mark feed item as read:', error)
      throw new Error('Failed to mark feed item as read')
    }
  }

  async performFeedItemAction(feedItemId: string, action: string): Promise<void> {
    try {
      await this.client.post(`/feed/${feedItemId}/action`, { action })
    } catch (error) {
      console.error('Failed to perform feed item action:', error)
      throw new Error('Failed to perform feed item action')
    }
  }

  // Conversation endpoints
  async getConversation(feedItemId: string): Promise<ConversationPayload | null> {
    try {
      const response = await this.client.get<ApiResponse<ConversationPayload>>(`/conversation/${feedItemId}`)
      return response.data.data || null
    } catch (error) {
      console.error('Failed to fetch conversation:', error)
      throw new Error('Failed to fetch conversation')
    }
  }

  async submitPrompt(feedItemId: string, prompt: string): Promise<void> {
    try {
      await this.client.post(`/conversation/${feedItemId}/prompt`, { prompt })
    } catch (error) {
      console.error('Failed to submit prompt:', error)
      throw new Error('Failed to submit prompt')
    }
  }

  // Stage management endpoints
  async moveItemToStage(itemId: string, targetStage: SDLCStage, fromStage?: SDLCStage, projectId?: string): Promise<{ brief?: any }> {
    try {
      const response = await this.client.post<ApiResponse<{ brief?: any }>>(`/idea/${itemId}/move-stage`, { 
        targetStage, 
        fromStage, 
        projectId 
      })
      return response.data.data || {}
    } catch (error) {
      console.error('Failed to move item to stage:', error)
      throw new Error('Failed to move item to stage')
    }
  }

  async getStageData(projectId: string): Promise<Record<SDLCStage, string[]>> {
    try {
      const response = await this.client.get<ApiResponse<Record<SDLCStage, string[]>>>(`/project/${projectId}/stages`)
      return response.data.data || { think: [], define: [], plan: [], build: [], validate: [] }
    } catch (error) {
      console.error('Failed to fetch stage data:', error)
      throw new Error('Failed to fetch stage data')
    }
  }

  // Product Brief endpoints
  async getProductBrief(briefId: string): Promise<any> {
    try {
      const response = await this.client.get<ApiResponse<any>>(`/product-brief/${briefId}`)
      return response.data.data || null
    } catch (error) {
      console.error('Failed to fetch product brief:', error)
      throw new Error('Failed to fetch product brief')
    }
  }

  async updateProductBrief(briefId: string, updates: any): Promise<void> {
    try {
      await this.client.put(`/product-brief/${briefId}`, updates)
    } catch (error) {
      console.error('Failed to update product brief:', error)
      throw new Error('Failed to update product brief')
    }
  }

  async freezeProductBrief(briefId: string): Promise<void> {
    try {
      await this.client.post(`/product-brief/${briefId}/freeze`)
    } catch (error) {
      console.error('Failed to freeze product brief:', error)
      throw new Error('Failed to freeze product brief')
    }
  }

  // Channel mapping endpoints
  async getChannelMapping(channelId: string): Promise<{ projectId: string } | null> {
    try {
      const response = await this.client.get<ApiResponse<{ projectId: string }>>(`/channel-mapping/${channelId}`)
      return response.data.data || null
    } catch (error) {
      console.error('Failed to fetch channel mapping:', error)
      return null
    }
  }

  async addChannelMapping(channelId: string, projectId: string): Promise<void> {
    try {
      await this.client.post('/channel-mapping', { channelId, projectId })
    } catch (error) {
      console.error('Failed to add channel mapping:', error)
      throw new Error('Failed to add channel mapping')
    }
  }

  // AI Integration endpoints
  async executeCommand(command: Command): Promise<void> {
    try {
      await this.client.post('/ai/execute', command)
    } catch (error) {
      console.error('Failed to execute command:', error)
      throw new Error('Failed to execute command')
    }
  }

  // Health check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    try {
      const response = await this.client.get<ApiResponse<{ status: string; timestamp: string }>>('/health')
      return response.data.data!
    } catch (error) {
      console.error('Health check failed:', error)
      throw new Error('Health check failed')
    }
  }

  // Socket.IO connection for real-time updates
  createSocketConnection(onMessage: (event: any) => void): Socket {
    const socket = io('http://localhost:5001', {
      transports: ['websocket', 'polling'],
      autoConnect: true,
    })
    
    socket.on('connect', () => {
      console.log('Socket.IO connection established')
    })
    
    socket.on('disconnect', () => {
      console.log('Socket.IO connection closed')
    })
    
    socket.on('connect_error', (error) => {
      console.error('Socket.IO connection error:', error)
    })
    
    // Listen for real-time updates
    socket.on('feed.update', (data) => {
      onMessage({ type: 'feed.update', data })
    })
    
    socket.on('feed.new', (data) => {
      onMessage({ type: 'feed.new', data })
    })
    
    socket.on('conversation.update', (data) => {
      onMessage({ type: 'conversation.update', data })
    })
    
    socket.on('project.update', (data) => {
      onMessage({ type: 'project.update', data })
    })
    
    socket.on('stage.moved', (data) => {
      onMessage({ type: 'stage.moved', data })
    })
    
    socket.on('brief.updated', (data) => {
      onMessage({ type: 'brief.updated', data })
    })
    
    socket.on('brief.frozen', (data) => {
      onMessage({ type: 'brief.frozen', data })
    })
    
    return socket
  }
}

// Create and export singleton instance
export const missionControlApi = new MissionControlApi()

// Export type for dependency injection
export type MissionControlApiType = typeof missionControlApi

export default missionControlApi