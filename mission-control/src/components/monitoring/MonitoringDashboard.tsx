/**
 * MonitoringDashboard Component - Main monitoring dashboard interface
 * 
 * This component implements the comprehensive monitoring dashboard as specified
 * in the design document. It provides real-time visibility into system events,
 * agent status, system health, and integrations.
 * 
 * Why this component exists:
 * - Provides centralized monitoring interface for the Software Factory
 * - Implements the cyber-grid visual theme with dark backgrounds and grid lines
 * - Displays real-time metrics and system status
 * - Enables proactive system management and issue resolution
 * 
 * For AI agents: This is the main monitoring dashboard that shows all system metrics.
 */

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { tokens } from '@/styles/tokens'
import { MetricCard } from './MetricCard'
import { EventStream } from './EventStream'
import { AgentStatusGrid } from './AgentStatusGrid'
import { SystemHealthPanel } from './SystemHealthPanel'
import { IntegrationStatus } from './IntegrationStatus'
import { AlertsPanel } from './AlertsPanel'
import { AnalyticsCharts } from './AnalyticsCharts'
import { ConnectionStatus } from './ConnectionStatus'
import { useMonitoringWebSocket } from '@/hooks/useMonitoringWebSocket'
import type { DashboardMetrics, MonitoringEvent, Alert } from '@/types/monitoring'

export const MonitoringDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())

  // Load dashboard metrics
  useEffect(() => {
    const loadMetrics = async () => {
      try {
        setError(null)
        const response = await fetch('/api/monitoring/dashboard')
        
        if (!response.ok) {
          throw new Error(`Failed to load metrics: ${response.statusText}`)
        }
        
        const data = await response.json()
        // Add status field to system health based on overall score
        if (data.system_health) {
          data.system_health.status = data.system_health.overall_score >= 80 ? 'healthy' : 
                                     data.system_health.overall_score >= 50 ? 'warning' : 'critical'
        }
        // Add activeAlerts field if not present
        if (!data.activeAlerts) {
          data.activeAlerts = []
        }
        setMetrics(data)
        setLastUpdate(new Date())
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load metrics')
        console.error('Failed to load dashboard metrics:', err)
      } finally {
        setLoading(false)
      }
    }

    loadMetrics()
    
    // Refresh metrics every 30 seconds - DISABLED to reduce API load
    // const interval = setInterval(loadMetrics, 30000)
    // return () => clearInterval(interval)
  }, [])

  // WebSocket connection for real-time updates
  const { subscribe } = useMonitoringWebSocket({
    autoConnect: true,
    throttle: {
      maxEventsPerSecond: 50,
      maxBatchSize: 20,
    },
  })

  useEffect(() => {

    // Subscribe to metrics updates
    const unsubscribeMetrics = subscribe('monitor.metrics', (newMetrics: DashboardMetrics) => {
      console.log('[MonitoringDashboard] Received metrics update:', newMetrics)
      
      // Add status field to system health based on overall score
      if (newMetrics.system_health) {
        newMetrics.system_health.status = newMetrics.system_health.overallScore >= 80 ? 'healthy' : 
                                         newMetrics.system_health.overallScore >= 50 ? 'warning' : 'critical'
      }
      // Add activeAlerts field if not present
      if (!newMetrics.activeAlerts) {
        newMetrics.activeAlerts = []
      }
      
      setMetrics(newMetrics)
      setLastUpdate(new Date())
      setError(null)
    })

    // Subscribe to alerts
    const unsubscribeAlerts = subscribe('monitor.alerts', (alert: Alert) => {
      console.log('[MonitoringDashboard] Received alert:', alert)
      
      setMetrics(prevMetrics => {
        if (!prevMetrics) return prevMetrics
        
        return {
          ...prevMetrics,
          activeAlerts: [alert, ...prevMetrics.activeAlerts].slice(0, 10), // Keep last 10 alerts
        }
      })
    })

    // Subscribe to events for the EventStream component
    const unsubscribeEvents = subscribe('monitor.events', (eventData: MonitoringEvent | { type: 'batch'; events: MonitoringEvent[] }) => {
      setMetrics(prevMetrics => {
        if (!prevMetrics) return prevMetrics
        
        let newEvents: MonitoringEvent[] = []
        
        if (typeof eventData === 'object' && 'type' in eventData && eventData.type === 'batch') {
          newEvents = (eventData as { type: 'batch'; events: MonitoringEvent[] }).events
        } else {
          newEvents = [eventData as MonitoringEvent]
        }
        
        // Update event metrics with new events
        const updatedRecentEvents = [...newEvents, ...prevMetrics.event_metrics.recentEvents]
          .slice(0, 100) // Keep last 100 events
        
        return {
          ...prevMetrics,
          event_metrics: {
            ...prevMetrics.event_metrics,
            recentEvents: updatedRecentEvents,
            totalEvents: prevMetrics.event_metrics.totalEvents + newEvents.length,
            // Update events per minute (simplified calculation)
            eventsPerMinute: Math.round((updatedRecentEvents.length / Math.min(60, updatedRecentEvents.length)) * 60),
          },
        }
      })
    })

    return () => {
      unsubscribeMetrics()
      unsubscribeAlerts()
      unsubscribeEvents()
    }
  }, [])

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-grid">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-white/20 border-t-white/60 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-white/60">Loading monitoring dashboard...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center bg-grid">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/20 flex items-center justify-center">
            <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-white mb-2">Failed to Load Dashboard</h3>
          <p className="text-white/60 text-sm mb-4">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  if (!metrics) {
    return (
      <div className="h-full flex items-center justify-center bg-grid">
        <div className="text-center">
          <p className="text-white/60">No metrics data available</p>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full overflow-auto bg-grid">
      {/* Dashboard Header */}
      <div className="layout-grid">
        <div className="col-8">
          <h2 className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>System Monitoring</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
            Real-time visibility into Software Factory operations
          </p>
        </div>
        <div className="col-4 flex items-center justify-end space-x-4">
          <div className="text-right">
            <p style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>Last updated</p>
            <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }} className="font-mono">
              {lastUpdate.toLocaleTimeString()}
            </p>
          </div>
          <ConnectionStatus compact={true} />
        </div>
      </div>

      {/* Top Row - 4 Metric Cards (3 cols each) */}
      <div className="layout-grid">
        <div className="col-3">
          <div className="card" data-accent="blue">
            <div style={{ color: 'var(--accent-blue)' }} className="metric-number">
              {Math.round(metrics.event_metrics.eventsPerMinute || 0)}
            </div>
            <div className="metric-label">EVENTS/MIN</div>
            <div className="metric-caption">→ Stable</div>
          </div>
        </div>
        
        <div className="col-3">
          <div className="card" data-accent="orange">
            <div style={{ color: 'var(--accent-orange)' }} className="metric-number">
              {Math.round(metrics.system_health.overallScore || 0)}%
            </div>
            <div className="metric-label">SYSTEM HEALTH</div>
            <div className="metric-caption">↘ Decreasing</div>
          </div>
        </div>
        
        <div className="col-3">
          <div className="card" data-accent="green">
            <div style={{ color: 'var(--accent-green)' }} className="metric-number">
              {Object.values(metrics.agent_metrics || {}).filter(a => a.status === 'running').length}
            </div>
            <div className="metric-label">ACTIVE AGENTS</div>
            <div className="metric-caption">→ Stable</div>
          </div>
        </div>
        
        <div className="col-3">
          <div className="card" data-accent="red">
            <div style={{ color: 'var(--accent-red)' }} className="metric-number">
              {Math.round((metrics.event_metrics.errorRate || 0) * 100)}%
            </div>
            <div className="metric-label">ERROR RATE</div>
            <div className="metric-caption">→ Stable</div>
          </div>
        </div>
      </div>

      {/* Middle Row - Analytics (8 cols) + Alerts (4 cols) */}
      <div className="layout-grid">
        <div className="col-8">
          <AnalyticsCharts metrics={metrics} />
        </div>
        <div className="col-4">
          <AlertsPanel alerts={metrics.activeAlerts} />
        </div>
      </div>

      {/* Bottom Row - Detailed Panels */}
      <div className="layout-grid">
        <div className="col-6 space-y-6">
          <SystemHealthPanel health={metrics.system_health} />
          <AgentStatusGrid agents={Object.values(metrics.agent_metrics || {})} />
        </div>
        
        <div className="col-6 space-y-6">
          <EventStream events={metrics.event_metrics.recentEvents || []} />
          <IntegrationStatus integrations={Object.values(metrics.integration_status || {})} />
        </div>
      </div>
    </div>
  )
}

export default MonitoringDashboard