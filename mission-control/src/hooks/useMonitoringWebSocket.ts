/**
 * useMonitoringWebSocket Hook
 * 
 * React hook for consuming real-time monitoring data via WebSocket.
 * Provides automatic connection management, subscription handling, and
 * data updates for monitoring components.
 * 
 * Features:
 * - Automatic connection and cleanup
 * - Topic subscription management
 * - Connection status monitoring
 * - Type-safe event handling
 * - Optimized re-rendering
 * 
 * Why this hook exists:
 * - Simplifies WebSocket usage in React components
 * - Handles connection lifecycle automatically
 * - Provides clean subscription management
 * - Ensures proper cleanup on unmount
 * 
 * For AI agents: This hook manages WebSocket connections for monitoring components.
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { monitoringWebSocket, MonitoringTopic, WebSocketConnectionStatus, MonitoringEventHandler } from '@/services/monitoring/websocketService'
import type { MonitoringEvent, DashboardMetrics, Alert } from '@/types/monitoring'

export interface UseMonitoringWebSocketOptions {
  topics?: MonitoringTopic[]
  autoConnect?: boolean
  throttle?: {
    maxEventsPerSecond?: number
    maxBatchSize?: number
  }
}

export interface UseMonitoringWebSocketReturn {
  connectionStatus: WebSocketConnectionStatus
  connect: () => Promise<void>
  disconnect: () => void
  subscribe: <T = any>(topic: MonitoringTopic, handler: (data: T) => void) => () => void
  isConnected: boolean
  isConnecting: boolean
  hasError: boolean
  error: string | null
  lastConnected: Date | null
  reconnectAttempts: number
}

export const useMonitoringWebSocket = (
  options: UseMonitoringWebSocketOptions = {}
): UseMonitoringWebSocketReturn => {
  const {
    topics = [],
    autoConnect = true,
    throttle,
  } = options

  const [connectionStatus, setConnectionStatus] = useState<WebSocketConnectionStatus>(
    monitoringWebSocket.getStatus()
  )

  const subscriptionsRef = useRef<Array<() => void>>([])
  const statusUnsubscribeRef = useRef<(() => void) | null>(null)

  // Configure throttling if provided
  useEffect(() => {
    if (throttle) {
      monitoringWebSocket.setThrottleOptions(throttle)
    }
  }, [throttle])

  // Subscribe to connection status changes
  useEffect(() => {
    const unsubscribe = monitoringWebSocket.onStatusChange((status) => {
      setConnectionStatus(status)
    })
    statusUnsubscribeRef.current = unsubscribe

    return () => {
      if (statusUnsubscribeRef.current) {
        statusUnsubscribeRef.current()
        statusUnsubscribeRef.current = null
      }
    }
  }, [])

  // Auto-connect if enabled
  useEffect(() => {
    if (autoConnect && !connectionStatus.connected && !connectionStatus.connecting) {
      monitoringWebSocket.connect().catch(error => {
        console.error('Failed to auto-connect to monitoring WebSocket:', error)
      })
    }
  }, [autoConnect, connectionStatus.connected, connectionStatus.connecting])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // Cleanup all subscriptions
      subscriptionsRef.current.forEach(unsubscribe => {
        try {
          unsubscribe()
        } catch (error) {
          console.error('Error unsubscribing from monitoring topic:', error)
        }
      })
      subscriptionsRef.current = []

      // Cleanup status subscription
      if (statusUnsubscribeRef.current) {
        statusUnsubscribeRef.current()
        statusUnsubscribeRef.current = null
      }

      // Disconnect if this was the last component using the service
      // Note: The service manages this internally via subscription counting
    }
  }, [])

  // Manual connection control
  const connect = useCallback(async (): Promise<void> => {
    try {
      await monitoringWebSocket.connect()
    } catch (error) {
      console.error('Failed to connect to monitoring WebSocket:', error)
      throw error
    }
  }, [])

  const disconnect = useCallback((): void => {
    monitoringWebSocket.disconnect()
  }, [])

  // Subscription management
  const subscribe = useCallback(<T = any>(
    topic: MonitoringTopic,
    handler: (data: T) => void
  ): (() => void) => {
    const unsubscribe = monitoringWebSocket.subscribe(topic, handler)
    subscriptionsRef.current.push(unsubscribe)

    // Return a cleanup function that also removes from our ref
    return () => {
      const index = subscriptionsRef.current.indexOf(unsubscribe)
      if (index > -1) {
        subscriptionsRef.current.splice(index, 1)
      }
      unsubscribe()
    }
  }, [])

  // Derived state for convenience
  const isConnected = connectionStatus.connected
  const isConnecting = connectionStatus.connecting
  const hasError = connectionStatus.error !== null
  const error = connectionStatus.error
  const lastConnected = connectionStatus.lastConnected
  const reconnectAttempts = connectionStatus.reconnectAttempts

  return {
    connectionStatus,
    connect,
    disconnect,
    subscribe,
    isConnected,
    isConnecting,
    hasError,
    error,
    lastConnected,
    reconnectAttempts,
  }
}

// Specialized hooks for specific monitoring data types

/**
 * Hook for monitoring real-time events
 */
export const useMonitoringEvents = (
  onEvent?: (event: MonitoringEvent) => void,
  options: Omit<UseMonitoringWebSocketOptions, 'topics'> = {}
) => {
  const { subscribe, ...websocket } = useMonitoringWebSocket({
    ...options,
    topics: ['monitor.events'],
  })

  useEffect(() => {
    if (!onEvent) return

    const unsubscribe = subscribe<MonitoringEvent | { type: 'batch'; events: MonitoringEvent[] }>(
      'monitor.events',
      (data) => {
        if (typeof data === 'object' && 'type' in data && data.type === 'batch') {
          // Handle batched events
          (data as { type: 'batch'; events: MonitoringEvent[] }).events.forEach(onEvent)
        } else {
          // Handle single event
          onEvent(data as MonitoringEvent)
        }
      }
    )

    return unsubscribe
  }, [onEvent, subscribe])

  return websocket
}

/**
 * Hook for monitoring dashboard metrics
 */
export const useMonitoringMetrics = (
  onMetrics?: (metrics: DashboardMetrics) => void,
  options: Omit<UseMonitoringWebSocketOptions, 'topics'> = {}
) => {
  const { subscribe, ...websocket } = useMonitoringWebSocket({
    ...options,
    topics: ['monitor.metrics'],
  })

  useEffect(() => {
    if (!onMetrics) return

    const unsubscribe = subscribe<DashboardMetrics>('monitor.metrics', onMetrics)
    return unsubscribe
  }, [onMetrics, subscribe])

  return websocket
}

/**
 * Hook for monitoring alerts
 */
export const useMonitoringAlerts = (
  onAlert?: (alert: Alert) => void,
  options: Omit<UseMonitoringWebSocketOptions, 'topics'> = {}
) => {
  const { subscribe, ...websocket } = useMonitoringWebSocket({
    ...options,
    topics: ['monitor.alerts'],
  })

  useEffect(() => {
    if (!onAlert) return

    const unsubscribe = subscribe<Alert>('monitor.alerts', onAlert)
    return unsubscribe
  }, [onAlert, subscribe])

  return websocket
}

export default useMonitoringWebSocket