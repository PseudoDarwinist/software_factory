/**
 * Core type definitions for Mission Control
 * 
 * This file contains all TypeScript interfaces and types used throughout the application.
 * 
 * Why these types exist:
 * - Provides type safety for all data structures
 * - Serves as documentation for API contracts
 * - Enables better IDE support and refactoring
 * 
 * For AI agents: These types define the exact shape of all data in the system.
 * When working with any data structure, check here first.
 */

// ========================================
// Core API Types
// ========================================

export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  timestamp: string
  version: string
}

export interface PaginatedResponse<T = any> {
  items: T[]
  total: number
  page: number
  pageSize: number
  hasMore: boolean
}

// ========================================
// Project Management Types
// ========================================

export type ProjectHealth = 'green' | 'amber' | 'red'

export type SystemMapStatus = 'pending' | 'in_progress' | 'completed' | 'failed' | 'error'

export interface ProjectSummary {
  id: string
  name: string
  health: ProjectHealth
  unreadCount: number
  iconUrl?: string
  lastActivity: string
  description?: string
  systemMapStatus?: SystemMapStatus
  systemMapError?: string
}

// ========================================
// Feed System Types
// ========================================

export type FeedSeverity = 'info' | 'amber' | 'red'

export type FeedKind = 
  | 'idea'                // Raw thought from Slack etc.
  | 'spec_change'         // Spec or design updated
  | 'ci_fail'             // Build/test failure
  | 'pr_review'           // Pull request needs review
  | 'qa_blocker'          // Manual QA flagged
  | 'agent_suggestion'    // AI proposes action
  | 'deployment'          // Deployment event
  | 'merge'               // Code merged

export interface FeedItem {
  id: string
  projectId: string
  severity: FeedSeverity
  kind: FeedKind
  title: string
  summary?: string
  createdAt: string
  updatedAt: string
  linkedArtifactIds: string[]
  unread: boolean
  actor: string // Who/what created this item
  metadata?: Record<string, any> & {
    stage?: SDLCStage
    channelId?: string
    slackTs?: string
    source?: string
  }
}

// ========================================
// Conversation System Types
// ========================================

export interface TimelineEvent {
  id: string
  time: string
  actor: string
  message: string
  eventType?: string
  metadata?: Record<string, any>
}

export type ConversationBlock = 
  | { type: 'timeline'; events: TimelineEvent[] }
  | { type: 'code_diff'; before: string; after: string; language: string; filePath: string }
  | { type: 'image_compare'; beforeUrl: string; afterUrl: string; caption?: string }
  | { type: 'spec_snippet'; textMd: string; sourceId: string }
  | { type: 'log_excerpt'; text: string; sourceId: string; level: 'info' | 'warn' | 'error' }
  | { type: 'metric'; label: string; value: number; unit?: string; trend?: 'up' | 'down' | 'stable' }
  | { type: 'llm_suggestion'; command: string; explanation: string; confidence: number }
  | { type: 'file_list'; files: FileChange[] }
  | { type: 'test_results'; results: TestResult[] }

export interface FileChange {
  path: string
  status: 'added' | 'modified' | 'deleted'
  additions: number
  deletions: number
}

export interface TestResult {
  name: string
  status: 'passed' | 'failed' | 'skipped'
  duration: number
  error?: string
}

export interface ConversationPayload {
  feedItemId: string
  blocks: ConversationBlock[]
  suggestedPrompt?: string
  context?: {
    project: ProjectSummary
    relatedItems: FeedItem[]
  }
}

// ========================================
// SDLC Stage Types
// ========================================

export type SDLCStage = 'think' | 'define' | 'plan' | 'build' | 'validate' | 'operator'

export interface StageTransition {
  from: SDLCStage
  to: SDLCStage
  itemId: string
  timestamp: string
  actor: string
}

// ========================================
// Product Brief Types
// ========================================

export interface ProductBrief {
  id: string
  itemId: string
  projectId: string
  problemStatement: string
  successMetrics: string[]
  risks: string[]
  competitiveAnalysis: string
  userStories: UserStory[]
  progress: number
  status: 'draft' | 'frozen'
  createdAt: string
  updatedAt: string
  version: number
  frozenAt?: string
}

export interface UserStory {
  id: string
  title: string
  description: string
  acceptanceCriteria: string[]
  priority: 'high' | 'medium' | 'low'
  estimatedEffort?: number
  assignee?: string
  status: 'draft' | 'ready' | 'in_progress' | 'review' | 'done'
}

// ========================================
// AI Integration Types
// ========================================

export interface AIProvider {
  id: string
  name: string
  status: 'active' | 'inactive' | 'error'
  capabilities: string[]
  lastUsed?: string
}

export interface AIResponse {
  provider: string
  model: string
  content: string
  confidence: number
  tokens: {
    input: number
    output: number
    total: number
  }
  latency: number
  timestamp: string
}

export interface Command {
  command: string
  args: Record<string, any>
  context?: Record<string, any>
}

// ========================================
// Kiro Integration Types
// ========================================

export interface KiroStatusResponse {
  available: boolean
  version?: string
  workspace_path?: string
}

export interface KiroGenerationResponse {
  success: boolean
  content?: string
  error?: string
  provider?: string
}

export interface KiroGenerationRequest {
  project_id: string
  idea_content: string
  requirements_content?: string
  design_content?: string
}

// ========================================
// Real-time Updates Types
// ========================================

export interface RealtimeEvent {
  type: 'feed.update' | 'feed.new' | 'conversation.update' | 'project.update' | 'system.notification' | 'stage.moved' | 'brief.updated' | 'brief.frozen'
  payload: any
  timestamp: string
  source: string
}

export interface SystemNotification {
  id: string
  type: 'info' | 'warning' | 'error' | 'success'
  title: string
  message: string
  timestamp: string
  actions?: Array<{
    label: string
    action: string
    variant?: 'primary' | 'secondary' | 'danger'
  }>
  autoClose?: boolean
  duration?: number
}

// ========================================
// UI State Types
// ========================================

export interface UIState {
  sidebarCollapsed: boolean
  selectedProject: string | null
  selectedFeedItem: string | null
  activeStage: SDLCStage
  theme: 'dark' | 'light'
  notifications: SystemNotification[]
}

export interface LoadingState {
  projects: boolean
  feed: boolean
  conversation: boolean
  action: boolean
}

export interface ErrorState {
  projects: string | null
  feed: string | null
  conversation: string | null
  action: string | null
}

// ========================================
// Animation Types
// ========================================

export interface AnimationConfig {
  duration: number
  easing: string
  delay?: number
}

export interface LiquidGlassEffect {
  opacity: number
  blur: number
  scale: number
  rotateX: number
  rotateY: number
  rotateZ: number
}

// ========================================
// Utility Types
// ========================================

export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>

export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P]
}

export type Awaited<T> = T extends Promise<infer U> ? U : T

// ========================================
// Task Management Types
// ========================================

export type TaskStatus = 'backlog' | 'ready' | 'running' | 'review' | 'done' | 'failed' | 'needs_rework'
export type TaskPriority = 'low' | 'medium' | 'high' | 'critical'

export interface Task {
  id: string
  spec_id: string
  project_id: string
  title: string
  description?: string
  task_number: string
  parent_task_id?: string
  status: TaskStatus
  priority: TaskPriority
  effort_estimate_hours?: number
  suggested_owner?: string
  assigned_to?: string
  assignment_confidence?: number
  assignment_reasoning?: string
  suggested_agent?: string
  agent_reasoning?: string
  effort_reasoning?: string
  likely_touches?: string[]
  goal_line?: string
  requirements_refs?: string[]
  depends_on?: string[]
  blocks?: string[]
  related_files?: string[]
  related_components?: string[]
  created_by?: string
  created_at?: string
  updated_by?: string
  updated_at?: string
  started_at?: string
  completed_at?: string
  started_by?: string
  completed_by?: string
  pr_url?: string
  build_status?: string
  agent?: string
  branchName?: string
  repoUrl?: string
  progressMessages?: Array<{
    timestamp: string
    message: string
    percent?: number
  }>
  touchedFiles?: string[]
  error?: string
}

export interface TaskContext {
  taskId: string
  context: string
  timestamp: string
}

export interface Agent {
  id: string
  name: string
  description: string
  capabilities?: string[]
  status?: 'active' | 'inactive' | 'error'
}

// ========================================
// Upload Session Types
// ========================================

export interface PRDInfo {
  id: string
  version: string
  status: 'draft' | 'frozen'
  created_at: string
  created_by?: string
  has_markdown: boolean
  has_json_summary: boolean
  sources: string[]
}

export interface SessionContext {
  session_id: string
  project_id: string
  description: string
  status: string
  ai_model_used?: string
  ai_analysis?: string
  prd_preview?: string
  combined_content?: string
  completeness_score?: any
  created_at: string
  updated_at: string
  processing_stats: {
    total_files: number
    completed_files: number
    error_files: number
    success_rate: number
  }
  files: any[]
  prd_info?: PRDInfo
}

// ========================================
// Integration Types (for existing systems)
// ========================================

export interface ExistingIntegration {
  businessInterface: {
    enabled: boolean
    endpoint: string
  }
  poInterface: {
    enabled: boolean
    endpoint: string
  }
  gooseAI: {
    enabled: boolean
    endpoint: string
  }
  modelGarden: {
    enabled: boolean
    endpoint: string
  }
}