/**
 * Validation types shared across Validate stage components
 */

export type ValidationCheckType = 'test' | 'deployment' | 'monitoring' | 'security' | 'performance'
export type ValidationCheckStatus = 'pending' | 'running' | 'success' | 'warning' | 'error'

export interface ValidationCheck {
  id: string
  name: string
  type: ValidationCheckType
  status: ValidationCheckStatus
  timestamp: Date
  duration?: number
  progress?: number
  metadata: Record<string, any>
  priority?: 'low' | 'medium' | 'high'
  // Optional project context for actions that need project scoping
  projectId?: string
  // Optional evidence when backend provides it on the check payload
  evidence?: ValidationEvidence
}

// Evidence and related models
export interface LogEntry {
  timestamp: Date
  level: 'info' | 'warn' | 'error'
  message: string
}

export interface TestResult {
  name: string
  status: 'pass' | 'fail' | 'skip'
  durationMs?: number
  errorMessage?: string
}

export interface PerformanceMetric {
  name: string
  value: number
  unit: string
  target?: number
}

export interface Screenshot {
  id: string
  url: string
  caption?: string
}

export interface ErrorDetail {
  message: string
  stack?: string
}

export interface ValidationEvidence {
  logs?: LogEntry[]
  testResults?: TestResult[]
  screenshots?: Screenshot[]
  performanceMetrics?: PerformanceMetric[]
  errors?: ErrorDetail[]
}

// Extended models for API integration
export type ValidationRunStatus = 'pending' | 'running' | 'completed' | 'failed' | 'blocked'

export interface ValidationApproval {
  id: string
  runId: string
  userId: string
  role: string
  status: 'pending' | 'approved' | 'rejected'
  reason?: string
  timestamp: string
}

export interface ValidationRun {
  id: string
  projectId: string
  prNumber?: number
  commitSha?: string
  branch?: string
  status: ValidationRunStatus
  startedAt: string
  completedAt?: string
  checks?: ValidationCheck[]
  approvals?: ValidationApproval[]
  metadata?: Record<string, any>
}

