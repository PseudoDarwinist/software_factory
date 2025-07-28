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
import type { 
  ApiResponse, 
  PaginatedResponse, 
  ProjectSummary, 
  FeedItem, 
  ConversationPayload,
  SDLCStage,
  Command,
  KiroStatusResponse,
  KiroGenerationResponse,
  KiroGenerationRequest
} from '@/types'

class MissionControlApi {
  private client: AxiosInstance
  private baseURL: string

  constructor(baseURL?: string) {
    // Always use same origin since Flask serves everything
    if (!baseURL) {
      baseURL = '/api'
    }
    
    this.baseURL = baseURL
    this.client = axios.create({
      baseURL,
      timeout: 120000, // 2 minutes for AI-powered specification generation
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
      const response = await this.client.get<ApiResponse<ProjectSummary[]>>('/mission-control/projects')
      return response.data.data || []
    } catch (error) {
      console.error('Failed to fetch projects:', error)
      throw new Error('Failed to fetch projects')
    }
  }

  async getProject(projectId: string): Promise<ProjectSummary | null> {
    try {
      const response = await this.client.get<ApiResponse<ProjectSummary>>(`/mission-control/projects/${projectId}`)
      return response.data.data || null
    } catch (error) {
      console.error('Failed to fetch project:', error)
      throw new Error('Failed to fetch project')
    }
  }

  async createProject(data: { name: string; repoUrl: string; githubToken?: string; slackChannels?: string[] }): Promise<ProjectSummary> {
    try {
      const response = await this.client.post<ApiResponse<ProjectSummary>>('/mission-control/projects', data)
      return response.data.data!
    } catch (error) {
      console.error('Failed to create project:', error)
      throw new Error('Failed to create project')
    }
  }

  async getSlackChannels(): Promise<Array<{ id: string; name: string; description: string }>> {
    try {
      const response = await this.client.get<ApiResponse<Array<{ id: string; name: string; description: string }>>>('/slack/channels')
      return response.data.data || []
    } catch (error) {
      console.error('Failed to fetch Slack channels:', error)
      throw new Error('Failed to fetch Slack channels')
    }
  }

  async updateProject(projectId: string, updates: Partial<ProjectSummary>): Promise<ProjectSummary> {
    try {
      const response = await this.client.patch<ApiResponse<ProjectSummary>>(`/mission-control/projects/${projectId}`, updates)
      return response.data.data!
    } catch (error) {
      console.error('Failed to update project:', error)
      throw new Error('Failed to update project')
    }
  }

  async deleteProject(projectId: string): Promise<void> {
    try {
      await this.client.delete(`/mission-control/projects/${projectId}`)
    } catch (error) {
      console.error('Failed to delete project:', error)
      throw new Error('Failed to delete project')
    }
  }

  async uploadProjectDocs(projectName: string, formData: FormData): Promise<{ projectId: string; docCount: number }> {
    try {
      const response = await this.client.post<ApiResponse<{ projectId: string; docCount: number }>>('/mission-control/projects/docs', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })
      return response.data.data!
    } catch (error) {
      console.error('Failed to upload project documents:', error)
      throw new Error('Failed to upload project documents')
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

  // Specification endpoints
  async getSpecification(itemId: string, projectId: string): Promise<any> {
    try {
      const response = await this.client.get<ApiResponse<any>>(`/specification/${itemId}`, {
        params: { projectId }
      })
      return response.data.data || null
    } catch (error) {
      console.error('Failed to fetch specification:', error)
      throw new Error('Failed to fetch specification')
    }
  }

  async updateSpecificationArtifact(
    specId: string, 
    projectId: string, 
    artifactType: 'requirements' | 'design' | 'tasks', 
    content: string
  ): Promise<any> {
    try {
      const response = await this.client.put<ApiResponse<any>>(`/specification/${specId}/artifact/${artifactType}`, {
        content,
        projectId
      })
      return response.data.data
    } catch (error) {
      console.error('Failed to update specification artifact:', error)
      throw new Error('Failed to update specification artifact')
    }
  }

  async markArtifactReviewed(
    specId: string, 
    projectId: string, 
    artifactType: 'requirements' | 'design' | 'tasks', 
    reviewNotes?: string
  ): Promise<any> {
    try {
      const response = await this.client.post<ApiResponse<any>>(`/specification/${specId}/artifact/${artifactType}/review`, {
        projectId,
        reviewNotes
      })
      return response.data.data
    } catch (error) {
      console.error('Failed to mark artifact as reviewed:', error)
      throw new Error('Failed to mark artifact as reviewed')
    }
  }

  async createSpecification(itemId: string, projectId: string): Promise<{ spec_id: string; processing_time: number; artifacts_created: number }> {
    try {
      const response = await this.client.post<ApiResponse<{ spec_id: string; processing_time: number; artifacts_created: number }>>(`/idea/${itemId}/create-spec`, {
        projectId
      })
      return response.data.data!
    } catch (error) {
      console.error('Failed to create specification:', error)
      throw new Error('Failed to create specification')
    }
  }

  async createSpecificationWithModelGarden(itemId: string, projectId: string): Promise<{ spec_id: string; processing_time: number; artifacts_created: number }> {
    try {
      const response = await this.client.post<ApiResponse<{ spec_id: string; processing_time: number; artifacts_created: number }>>(`/idea/${itemId}/create-spec-model-garden`, {
        projectId
      })
      return response.data.data!
    } catch (error) {
      console.error('Failed to create specification with AI Model Garden:', error)
      throw new Error('Failed to create specification with AI Model Garden')
    }
  }

  async generateDesignDocument(specId: string, projectId: string): Promise<any> {
    try {
      const response = await this.client.post<ApiResponse<any>>(`/specification/${specId}/generate-design`, {
        projectId
      }, {
        timeout: 360000 // 6 minutes for Claude Code SDK design generation
      })
      return response.data.data
    } catch (error) {
      console.error('Failed to generate design document:', error)
      throw new Error('Failed to generate design document')
    }
  }

  async generateTasksDocument(specId: string, projectId: string): Promise<any> {
    try {
      const response = await this.client.post(`/specification/${specId}/generate-tasks`, { projectId })
      // If backend streams, we get 202 with empty body – simply return null
      if (response.status === 202) return null
      return (response.data as any)?.data || null
    } catch (error) {
      console.error('Failed to generate tasks document:', error)
      throw new Error('Failed to generate tasks document')
    }
  }

  async freezeSpecification(specId: string, projectId: string): Promise<void> {
    try {
      await this.client.post(`/specification/${specId}/freeze`, { projectId })
    } catch (error) {
      console.error('Failed to freeze specification:', error)
      throw new Error('Failed to freeze specification')
    }
  }

  async askAIAssistant(request: { query: string; context: any }): Promise<{ response: string }> {
    try {
      const response = await this.client.post<ApiResponse<{ response: string }>>('/ai/assistant', request)
      return response.data.data!
    } catch (error) {
      console.error('Failed to ask AI assistant:', error)
      throw new Error('Failed to ask AI assistant')
    }
  }

  // Product Brief endpoints (legacy - keeping for backward compatibility)
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

  // Kiro Integration endpoints
  async checkKiroStatus(): Promise<KiroStatusResponse> {
    try {
      const response = await this.client.get<ApiResponse<KiroStatusResponse>>('/kiro/status')
      return response.data.data!
    } catch (error) {
      console.error('Failed to check Kiro status:', error)
      // Return safe fallback when Kiro is not available
      return { available: false }
    }
  }

  async generateRequirementsWithKiro(projectId: string, ideaContent: string): Promise<KiroGenerationResponse> {
    try {
      const requestData: KiroGenerationRequest = {
        project_id: projectId,
        idea_content: ideaContent
      }
      
      const response = await this.client.post<ApiResponse<KiroGenerationResponse>>('/kiro/generate-requirements', requestData)
      
      if (!response.data.data) {
        throw new Error('No data received from Kiro service')
      }
      
      return response.data.data
    } catch (error) {
      console.error('Failed to generate requirements with Kiro:', error)
      
      // Return structured error response instead of throwing
      if (error instanceof Error) {
        return {
          success: false,
          error: error.message,
          provider: 'kiro'
        }
      }
      
      return {
        success: false,
        error: 'Unknown error occurred while generating requirements',
        provider: 'kiro'
      }
    }
  }

  async generateDesignWithKiro(projectId: string, ideaContent: string, requirementsContent: string): Promise<KiroGenerationResponse> {
    try {
      const requestData: KiroGenerationRequest = {
        project_id: projectId,
        idea_content: ideaContent,
        requirements_content: requirementsContent
      }
      
      const response = await this.client.post<ApiResponse<KiroGenerationResponse>>('/kiro/generate-design', requestData)
      
      if (!response.data.data) {
        throw new Error('No data received from Kiro service')
      }
      
      return response.data.data
    } catch (error) {
      console.error('Failed to generate design with Kiro:', error)
      
      // Return structured error response instead of throwing
      if (error instanceof Error) {
        return {
          success: false,
          error: error.message,
          provider: 'kiro'
        }
      }
      
      return {
        success: false,
        error: 'Unknown error occurred while generating design',
        provider: 'kiro'
      }
    }
  }

  async generateTasksWithKiro(projectId: string, ideaContent: string, requirementsContent: string, designContent: string): Promise<KiroGenerationResponse> {
    try {
      const requestData: KiroGenerationRequest = {
        project_id: projectId,
        idea_content: ideaContent,
        requirements_content: requirementsContent,
        design_content: designContent
      }
      
      const response = await this.client.post<ApiResponse<KiroGenerationResponse>>('/kiro/generate-tasks', requestData)
      
      if (!response.data.data) {
        throw new Error('No data received from Kiro service')
      }
      
      return response.data.data
    } catch (error) {
      console.error('Failed to generate tasks with Kiro:', error)
      
      // Return structured error response instead of throwing
      if (error instanceof Error) {
        return {
          success: false,
          error: error.message,
          provider: 'kiro'
        }
      }
      
      return {
        success: false,
        error: 'Unknown error occurred while generating tasks',
        provider: 'kiro'
      }
    }
  }

  // Polling-based updates system
  private pollingInterval: NodeJS.Timeout | null = null
  private pollingCallbacks: ((event: any) => void)[] = []
  private lastUpdate: Record<string, number> = {}

  startPolling(onMessage: (event: any) => void, interval: number = 3000): () => void {
    this.pollingCallbacks.push(onMessage)
    
    // Start polling if not already started
    if (!this.pollingInterval) {
      this.pollingInterval = setInterval(() => {
        this.pollForUpdates()
      }, interval)
      
      console.log(`Started polling for updates (interval: ${interval}ms)`)
    }
    
    // Return cleanup function
    return () => {
      this.pollingCallbacks = this.pollingCallbacks.filter(cb => cb !== onMessage)
      
      // Stop polling if no more callbacks
      if (this.pollingCallbacks.length === 0 && this.pollingInterval) {
        clearInterval(this.pollingInterval)
        this.pollingInterval = null
        console.log('Stopped polling for updates')
      }
    }
  }

  private async pollForUpdates(): Promise<void> {
    try {
      // Poll for system status and updates
      const response = await this.client.get<ApiResponse<{
        timestamp: string
        projects_updated: number
        feed_updated: number
        active_jobs: number
        system_health: string
      }>>('/status')
      
      const status = response.data.data
      if (!status) return
      
      const currentTime = Date.now()
      
      // Check for project updates
      if (status.projects_updated > (this.lastUpdate.projects || 0)) {
        this.lastUpdate.projects = status.projects_updated
        this.notifyCallbacks({ type: 'projects.updated', payload: { timestamp: status.timestamp } })
      }
      
      // Check for feed updates
      if (status.feed_updated > (this.lastUpdate.feed || 0)) {
        this.lastUpdate.feed = status.feed_updated
        this.notifyCallbacks({ type: 'feed.updated', payload: { timestamp: status.timestamp } })
      }
      
      // Check for active jobs
      if (status.active_jobs > 0) {
        this.notifyCallbacks({ type: 'jobs.active', payload: { count: status.active_jobs } })
      }
      
      // Check system health
      if (status.system_health !== 'healthy') {
        this.notifyCallbacks({ type: 'system.health', payload: { status: status.system_health } })
      }
      
    } catch (error) {
      console.error('Polling error:', error)
      // Don't notify callbacks about polling errors unless it's persistent
    }
  }

  private notifyCallbacks(event: any): void {
    this.pollingCallbacks.forEach(callback => {
      try {
        callback(event)
      } catch (error) {
        console.error('Error in polling callback:', error)
      }
    })
  }

  // Check for specific data updates
  async checkForUpdates(lastCheck?: Date): Promise<{
    projects: boolean
    feed: boolean
    conversations: boolean
  }> {
    try {
      const timestamp = lastCheck ? lastCheck.getTime() : 0
      const response = await this.client.get<ApiResponse<{
        projects_updated: number
        feed_updated: number
        conversations_updated: number
      }>>('/updates', {
        params: { since: timestamp }
      })
      
      const updates = response.data.data || {
        projects_updated: 0,
        feed_updated: 0,
        conversations_updated: 0
      }
      
      return {
        projects: updates.projects_updated > 0,
        feed: updates.feed_updated > 0,
        conversations: updates.conversations_updated > 0
      }
    } catch (error) {
      console.error('Failed to check for updates:', error)
      return { projects: false, feed: false, conversations: false }
    }
  }

  // Task management endpoints
  async getTasks(projectId?: string, status?: string): Promise<any[]> {
    try {
      const params = new URLSearchParams()
      if (projectId) params.append('project_id', projectId)
      if (status) params.append('status', status)
      
      const response = await this.client.get<{ tasks: any[]; total: number }>(`/tasks?${params.toString()}`)
      return response.data.tasks || []
    } catch (error) {
      console.error('Failed to fetch tasks:', error)
      throw new Error('Failed to fetch tasks')
    }
  }

  async getTaskContext(taskId: string): Promise<{ taskId: string; context: string; timestamp: string }> {
    try {
      const response = await this.client.get<ApiResponse<{ taskId: string; context: string; timestamp: string }>>(`/tasks/${taskId}/context`)
      return response.data.data!
    } catch (error) {
      console.error('Failed to fetch task context:', error)
      throw new Error('Failed to fetch task context')
    }
  }

  async startTask(taskId: string, agentId: string, options?: {
    contextOptions?: { spec_files?: boolean; requirements?: boolean; design?: boolean; task?: boolean; code_paths?: boolean };
    branchName?: string;
    baseBranch?: string;
  }): Promise<void> {
    try {
      const payload: any = { agentId }
      if (options?.contextOptions) payload.contextOptions = options.contextOptions
      if (options?.branchName) payload.branchName = options.branchName
      if (options?.baseBranch) payload.baseBranch = options.baseBranch
      
      await this.client.post(`/tasks/${taskId}/start`, payload)
    } catch (error) {
      console.error('Failed to start task:', error)
      throw new Error('Failed to start task')
    }
  }

  async retryTask(taskId: string, agentId: string): Promise<void> {
    try {
      await this.client.post(`/tasks/${taskId}/retry`, { agentId })
    } catch (error) {
      console.error('Failed to retry task:', error)
      throw new Error('Failed to retry task')
    }
  }

  async cancelTask(taskId: string): Promise<void> {
    try {
      await this.client.post(`/tasks/${taskId}/cancel`)
    } catch (error) {
      console.error('Failed to cancel task:', error)
      throw new Error('Failed to cancel task')
    }
  }

  async getTaskDetail(taskId: string): Promise<any> {
    try {
      const response = await this.client.get<ApiResponse<any>>(`/tasks/${taskId}`)
      return response.data.data
    } catch (error) {
      console.error('Failed to fetch task detail:', error)
      throw new Error('Failed to fetch task detail')
    }
  }

  async checkTaskConflicts(files: string[]): Promise<any[]> {
    try {
      const response = await this.client.get<ApiResponse<{ conflicts: any[] }>>(`/tasks/conflicts?files=${files.join(',')}`)
      return response.data.data?.conflicts || []
    } catch (error) {
      console.error('Failed to check task conflicts:', error)
      throw new Error('Failed to check task conflicts')
    }
  }

  // GitHub integration endpoints
  async getGitHubStatus(projectId?: string): Promise<{ connected: boolean; repo_accessible: boolean; repo_url?: string; base_branch?: string; error?: string }> {
    try {
      const params = projectId ? { project_id: projectId } : {}
      const response = await this.client.get<{ connected: boolean; repo_accessible: boolean; repo_url?: string; base_branch?: string; error?: string }>('/github/status', { params })
      return response.data
    } catch (error) {
      console.error('Failed to get GitHub status:', error)
      return { connected: false, repo_accessible: false, error: 'Failed to check GitHub status' }
    }
  }

  // Task intelligence endpoints
  async updateTaskField(taskId: string, field: string, value: any): Promise<{ message: string; task: any }> {
    try {
      const response = await this.client.patch<ApiResponse<{ message: string; task: any }>>(`/tasks/${taskId}/update-field`, {
        field,
        value
      })
      return response.data.data!
    } catch (error) {
      console.error('Failed to update task field:', error)
      throw new Error('Failed to update task field')
    }
  }

  async suggestAssignee(taskId: string): Promise<{ assignee: string; confidence: number; reasoning: string }> {
    try {
      const response = await this.client.post<ApiResponse<{ assignee: string; confidence: number; reasoning: string }>>(`/tasks/${taskId}/suggest-assignee`)
      return response.data.data!
    } catch (error) {
      console.error('Failed to get assignee suggestion:', error)
      throw new Error('Failed to get assignee suggestion')
    }
  }

  async suggestEstimate(taskId: string): Promise<{ hours: number; confidence: number; reasoning: string }> {
    try {
      const response = await this.client.post<ApiResponse<{ hours: number; confidence: number; reasoning: string }>>(`/tasks/${taskId}/suggest-estimate`)
      return response.data.data!
    } catch (error) {
      console.error('Failed to get effort estimate suggestion:', error)
      throw new Error('Failed to get effort estimate suggestion')
    }
  }

  async suggestAgent(taskId: string): Promise<{ agent: string; confidence: number; reasoning: string }> {
    try {
      const response = await this.client.post<ApiResponse<{ agent: string; confidence: number; reasoning: string }>>(`/tasks/${taskId}/suggest-agent`)
      return response.data.data!
    } catch (error) {
      console.error('Failed to get agent suggestion:', error)
      throw new Error('Failed to get agent suggestion')
    }
  }

  // Build stage specific endpoints
  async getBuildTasks(projectId?: string): Promise<any[]> {
    try {
      const params = new URLSearchParams()
      if (projectId) params.append('project_id', projectId)
      // Filter to only build-related statuses
      params.append('status', 'running,review,failed')
      
      const response = await this.client.get<{ tasks: any[]; total: number }>(`/tasks?${params.toString()}`)
      return response.data.tasks || []
    } catch (error) {
      console.error('Failed to fetch build tasks:', error)
      throw new Error('Failed to fetch build tasks')
    }
  }

  async getPRDiff(prUrl: string): Promise<string | null> {
    try {
      // Mock implementation - in real app would fetch from GitHub API
      // This would extract owner/repo/pr_number from prUrl and call GitHub API
      return `--- a/ui/theme/tokens.css
+++ b/ui/theme/tokens.css
@@ -100,6 +100,10 @@
   text-100: #FFFFFF;
+  text-200: #F0F0F0;
+  
+  bg-900: #0A0A10;
+  bg-800: #1A1A20;`
    } catch (error) {
      console.error('Failed to fetch PR diff:', error)
      return null
    }
  }

  async approvePR(taskId: string): Promise<void> {
    try {
      await this.client.post(`/tasks/${taskId}/approve`)
    } catch (error) {
      console.error('Failed to approve PR:', error)
      throw new Error('Failed to approve PR')
    }
  }

  async convertPRToReady(taskId: string): Promise<void> {
    try {
      await this.client.post(`/tasks/${taskId}/convert-pr-to-ready`)
    } catch (error) {
      console.error('Failed to convert PR to ready:', error)
      throw new Error('Failed to convert PR to ready')
    }
  }
}

// Create and export singleton instance
export const missionControlApi = new MissionControlApi()

// Export type for dependency injection
export type MissionControlApiType = typeof missionControlApi

export default missionControlApi