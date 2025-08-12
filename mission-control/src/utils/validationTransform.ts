import type { ValidationCheck, ValidationRun, ValidationEvidence, LogEntry, TestResult, PerformanceMetric, Screenshot, ErrorDetail } from '@/types/validation'

export function toDate(value: any): Date | undefined {
  if (!value) return undefined
  if (value instanceof Date) return value
  const d = new Date(value)
  return isNaN(d.getTime()) ? undefined : d
}

export function normalizeCheck(input: any): ValidationCheck {
  const c: ValidationCheck = {
    id: String(input.id),
    name: String(input.name),
    type: input.type,
    status: input.status,
    timestamp: toDate(input.timestamp) || new Date(),
    duration: input.duration != null ? Number(input.duration) : undefined,
    progress: input.progress != null ? Number(input.progress) : undefined,
    metadata: input.metadata || {},
    priority: input.priority,
    projectId: input.projectId || input.project_id,
  }
  // Normalize nested evidence if present on the check payload
  if (input.evidence) {
    c.evidence = normalizeEvidence(input.evidence)
  }
  return c
}

export function normalizeRun(input: any): ValidationRun {
  // Map backend status -> UI status
  const rawStatus = input.status
  const statusMap: Record<string, ValidationRun['status']> = {
    initializing: 'pending',
    running: 'running',
    success: 'completed',
    failure: 'failed',
    cancelled: 'failed',
  }
  const mappedStatus: ValidationRun['status'] = statusMap[rawStatus] || rawStatus
  const run: ValidationRun = {
    id: String(input.id),
    projectId: input.projectId || input.project_id,
    prNumber: input.prNumber ?? input.pr_number,
    commitSha: input.commitSha ?? input.commit_sha,
    branch: input.branch,
    status: mappedStatus,
    startedAt: (toDate(input.startedAt ?? input.started_at) || new Date()).toISOString(),
    completedAt: toDate(input.completedAt ?? input.completed_at)?.toISOString(),
    checks: Array.isArray(input.checks) ? input.checks.map(normalizeCheck) : [],
    approvals: input.approvals || [],
    metadata: input.metadata || {},
  }
  return run
}

function toLogEntry(input: any): LogEntry | null {
  if (!input) return null
  const ts = toDate(input.timestamp) || new Date()
  const level = typeof input.level === 'string' ? input.level : 'info'
  const message = typeof input.message === 'string' ? input.message : String(input.message ?? '')
  return { timestamp: ts, level, message } as LogEntry
}

function toTestResult(input: any): TestResult | null {
  if (!input) return null
  const name = typeof input.name === 'string' ? input.name : 'test'
  const status = input.status === 'fail' || input.status === 'skip' ? input.status : 'pass'
  const durationMs = input.durationMs != null ? Number(input.durationMs) : input.duration != null ? Number(input.duration) : undefined
  const errorMessage = typeof input.errorMessage === 'string' ? input.errorMessage : input.error || undefined
  return { name, status, durationMs, errorMessage }
}

function toPerformanceMetric(input: any): PerformanceMetric | null {
  if (!input) return null
  const name = typeof input.name === 'string' ? input.name : 'metric'
  const value = Number(input.value ?? 0)
  const unit = typeof input.unit === 'string' ? input.unit : ''
  const target = input.target != null ? Number(input.target) : undefined
  return { name, value, unit, target }
}

function toScreenshot(input: any): Screenshot | null {
  if (!input) return null
  const id = String(input.id ?? input.url ?? Date.now())
  const url = String(input.url ?? '')
  const caption = typeof input.caption === 'string' ? input.caption : undefined
  return { id, url, caption }
}

function toErrorDetail(input: any): ErrorDetail | null {
  if (!input) return null
  const message = typeof input.message === 'string' ? input.message : String(input.message ?? input.error ?? 'Error')
  const stack = typeof input.stack === 'string' ? input.stack : undefined
  return { message, stack }
}

export function normalizeEvidence(input: any): ValidationEvidence {
  const logs = Array.isArray(input?.logs) ? (input.logs.map(toLogEntry).filter(Boolean) as LogEntry[]) : undefined
  const testResults = Array.isArray(input?.testResults ?? input?.tests)
    ? ((input.testResults ?? input.tests).map(toTestResult).filter(Boolean) as TestResult[])
    : undefined
  const performanceMetrics = Array.isArray(input?.performanceMetrics ?? input?.metrics)
    ? ((input.performanceMetrics ?? input.metrics).map(toPerformanceMetric).filter(Boolean) as PerformanceMetric[])
    : undefined
  const screenshots = Array.isArray(input?.screenshots) ? (input.screenshots.map(toScreenshot).filter(Boolean) as Screenshot[]) : undefined
  const errors = Array.isArray(input?.errors) ? (input.errors.map(toErrorDetail).filter(Boolean) as ErrorDetail[]) : undefined
  return { logs, testResults, performanceMetrics, screenshots, errors }
}

