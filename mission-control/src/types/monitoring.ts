/**
 * Monitoring Types - Type definitions for monitoring dashboard
 * 
 * This file contains all TypeScript interfaces and types used for the monitoring system.
 * 
 * Why these types exist:
 * - Provides type safety for monitoring data structures
 * - Serves as documentation for monitoring API contracts
 * - Enables better IDE support and refactoring
 * 
 * For AI agents: These types define the exact shape of all monitoring data.
 */

// ========================================
// System Health Types
// ========================================

export type HealthStatus = 'healthy' | 'warning' | 'critical'

export interface SystemHealth {
  overallScore: number // 0-100
  status: HealthStatus
  components: {
    database?: ComponentHealth
    redis?: ComponentHealth
    websocket?: ComponentHealth
    apis?: ComponentHealth
  }
  resources: {
    cpuUsage?: number
    memoryUsage?: number
    diskUsage?: number
    networkLatency?: number
  }
  performance: {
    responseTime?: number
    throughput?: number
    errorRate?: number
  }
  lastUpdated?: string
}

export interface ComponentHealth {
  status: HealthStatus
  responseTime?: number
  errorRate?: number
  lastCheck: string
  message?: string
}

// ========================================
// Event Monitoring Types
// ========================================

export interface EventMetrics {
  totalEvents: number
  eventsPerMinute: number
  eventsByType: Record<string, number>
  averageProcessingTime: number
  errorRate: number
  recentEvents: MonitoringEvent[]
  lastUpdated: string
}

export interface MonitoringEvent {
  id: string
  type: string
  source: string
  timestamp: string
  payload: Record<string, any>
  processingTime?: number
  success: boolean
  error?: string
}

// ========================================
// Agent Monitoring Types
// ========================================

export type AgentStatus = 'running' | 'stopped' | 'error' | 'paused'

export interface AgentMetrics {
  id: string
  name: string
  status: AgentStatus
  metrics: {
    eventsProcessed: number
    successRate: number
    averageProcessingTime: number
    currentLoad: number
    lastActivity: string
  }
  configuration: Record<string, any>
  logs: LogEntry[]
  lastHeartbeat: string
}

export interface LogEntry {
  timestamp: string
  level: 'info' | 'warn' | 'error' | 'debug'
  message: string
  metadata?: Record<string, any>
}

// ========================================
// Integration Monitoring Types
// ========================================

export interface IntegrationStatus {
  id: string
  name: string
  status: HealthStatus
  metrics: {
    successRate: number
    responseTime: number
    apiUsage: number
    rateLimitRemaining?: number
  }
  lastSuccessfulConnection: string
  lastError?: string
  configuration: Record<string, any>
}

// ========================================
// Alert Types
// ========================================

export type AlertSeverity = 'critical' | 'warning' | 'info'

export interface Alert {
  id: string
  type: AlertSeverity
  title: string
  description: string
  source: string
  timestamp: string
  acknowledged: boolean
  acknowledgedBy?: string
  acknowledgedAt?: string
  resolved: boolean
  resolvedAt?: string
  metadata: Record<string, any>
}

export interface AlertThreshold {
  id: string
  metric: string
  operator: 'gt' | 'lt' | 'eq' | 'gte' | 'lte'
  value: number
  severity: AlertSeverity
  enabled: boolean
  description: string
}

// ========================================
// Dashboard Data Types
// ========================================

export interface DashboardMetrics {
  system_health: SystemHealth
  event_metrics: EventMetrics
  agent_metrics: Record<string, AgentMetrics>
  integration_status: Record<string, IntegrationStatus>
  activeAlerts: Alert[]
  timestamp: string
}

export interface MetricDataPoint {
  timestamp: string
  value: number
  label?: string
}

export interface ChartData {
  data: MetricDataPoint[]
  title: string
  unit?: string
  color: string
  trend?: 'up' | 'down' | 'stable'
}

// ========================================
// WebSocket Event Types
// ========================================

export interface MonitoringWebSocketEvent {
  type: 'monitor.events' | 'monitor.metrics' | 'monitor.alerts'
  payload: any
  timestamp: string
}

// ========================================
// API Response Types
// ========================================

export interface MonitoringApiResponse<T = any> {
  success: boolean
  data?: T
  error?: string
  timestamp: string
}

export interface EventSearchParams {
  query?: string
  type?: string
  source?: string
  startTime?: string
  endTime?: string
  limit?: number
  offset?: number
}

export interface EventSearchResponse {
  events: MonitoringEvent[]
  total: number
  hasMore: boolean
}