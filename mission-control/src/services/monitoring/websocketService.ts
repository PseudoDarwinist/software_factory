/**
 * WebSocket Service for Monitoring Dashboard
 * 
 * This service handles real-time WebSocket connections for monitoring updates.
 * It provides connection management, automatic reconnection, message throttling,
 * and event streaming for the monitoring dashboard.
 * 
 * Features:
 * - Automatic connection management and reconnection
 * - Subscription to multiple monitoring topics
 * - Message throttling for high-volume events
 * - Connection status monitoring
 * - Error handling and resilience
 * 
 * Why this service exists:
 * - Provides real-time updates for monitoring data
 * - Implements the WebSocket requirements from the design spec
 * - Handles connection reliability and error recovery
 * - Supports monitoring topics: monitor.events, monitor.metrics, monitor.alerts
 * 
 * For AI agents: This is the WebSocket service for real-time monitoring updates.
 */

import { io, Socket } from 'socket.io-client'
import type { MonitoringWebSocketEvent, MonitoringEvent, DashboardMetrics, Alert } from '@/types/monitoring'

export type MonitoringTopic = 'monitor.events' | 'monitor.metrics' | 'monitor.alerts'

export interface WebSocketConnectionStatus {
  connected: boolean
  connecting: boolean
  error: string | null
  lastConnected: Date | null
  reconnectAttempts: number
}

export interface MonitoringEventHandler {
  (data: any): void
}

export interface ThrottleOptions {
  maxEventsPerSecond: number
  maxBatchSize: number
}

class MonitoringWebSocketService {
  private socket: Socket | null = null
  private connectionStatus: WebSocketConnectionStatus = {
    connected: false,
    connecting: false,
    error: null,
    lastConnected: null,
    reconnectAttempts: 0,
  }

  private subscribers: Map<MonitoringTopic, Set<MonitoringEventHandler>> = new Map()
  private statusSubscribers: Set<(status: WebSocketConnectionStatus) => void> = new Set()

  // Throttling for high-volume events
  private eventQueue: Array<{ topic: MonitoringTopic; data: any }> = []
  private throttleTimer: NodeJS.Timeout | null = null
  private throttleOptions: ThrottleOptions = {
    maxEventsPerSecond: 100,
    maxBatchSize: 50,
  }

  // Connection management
  private reconnectTimer: NodeJS.Timeout | null = null
  private maxReconnectAttempts = 10
  private reconnectBaseDelay = 1000 // Start with 1 second

  constructor() {
    this.initializeSubscriptionMaps()
  }

  private initializeSubscriptionMaps(): void {
    const topics: MonitoringTopic[] = ['monitor.events', 'monitor.metrics', 'monitor.alerts']
    topics.forEach(topic => {
      this.subscribers.set(topic, new Set())
    })
  }

  /**
   * Connect to the WebSocket server
   */
  async connect(): Promise<void> {
    if (this.socket?.connected) {
      return
    }

    if (this.connectionStatus.connecting) {
      return
    }

    this.updateConnectionStatus({ connecting: true, error: null })

    try {
      // Construct WebSocket URL
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = window.location.host
      const socketUrl = `${protocol}//${host}`

      console.log('[MonitoringWS] Connecting to:', socketUrl)

      this.socket = io(socketUrl, {
        transports: ['websocket'],
        timeout: 10000,
        forceNew: true,
        auth: {
          // Include auth token if available
          token: localStorage.getItem('auth_token'),
        },
      })

      this.setupEventHandlers()
      
      return new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          reject(new Error('Connection timeout'))
        }, 10000)

        this.socket!.once('connect', () => {
          clearTimeout(timeout)
          this.onConnected()
          resolve()
        })

        this.socket!.once('connect_error', (error) => {
          clearTimeout(timeout)
          this.onConnectionError(error)
          reject(error)
        })
      })
    } catch (error) {
      this.onConnectionError(error as Error)
      throw error
    }
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    if (this.throttleTimer) {
      clearTimeout(this.throttleTimer)
      this.throttleTimer = null
    }

    if (this.socket) {
      console.log('[MonitoringWS] Disconnecting...')
      this.socket.disconnect()
      this.socket = null
    }

    this.updateConnectionStatus({
      connected: false,
      connecting: false,
      error: null,
      reconnectAttempts: 0,
    })
  }

  /**
   * Subscribe to a monitoring topic
   */
  subscribe(topic: MonitoringTopic, handler: MonitoringEventHandler): () => void {
    const topicSubscribers = this.subscribers.get(topic)
    if (!topicSubscribers) {
      console.error(`[MonitoringWS] Unknown topic: ${topic}`)
      return () => {}
    }

    topicSubscribers.add(handler)
    console.log(`[MonitoringWS] Subscribed to ${topic} (${topicSubscribers.size} total)`)

    // If connected, subscribe to the topic on the server
    if (this.socket?.connected) {
      this.socket.emit('subscribe', topic)
    }

    // Return unsubscribe function
    return () => {
      topicSubscribers.delete(handler)
      console.log(`[MonitoringWS] Unsubscribed from ${topic} (${topicSubscribers.size} remaining)`)
      
      // If no more subscribers for this topic, unsubscribe on server
      if (topicSubscribers.size === 0 && this.socket?.connected) {
        this.socket.emit('unsubscribe', topic)
      }
    }
  }

  /**
   * Subscribe to connection status changes
   */
  onStatusChange(handler: (status: WebSocketConnectionStatus) => void): () => void {
    this.statusSubscribers.add(handler)
    
    // Send current status immediately
    handler(this.connectionStatus)
    
    return () => {
      this.statusSubscribers.delete(handler)
    }
  }

  /**
   * Get current connection status
   */
  getStatus(): WebSocketConnectionStatus {
    return { ...this.connectionStatus }
  }

  /**
   * Configure throttling options
   */
  setThrottleOptions(options: Partial<ThrottleOptions>): void {
    this.throttleOptions = { ...this.throttleOptions, ...options }
    console.log('[MonitoringWS] Updated throttle options:', this.throttleOptions)
  }

  private setupEventHandlers(): void {
    if (!this.socket) return

    this.socket.on('connect', this.onConnected.bind(this))
    this.socket.on('disconnect', this.onDisconnected.bind(this))
    this.socket.on('connect_error', this.onConnectionError.bind(this))
    this.socket.on('reconnect', this.onReconnected.bind(this))
    this.socket.on('error', this.onError.bind(this))

    // Subscribe to monitoring topics
    this.socket.on('monitor.events', (data) => this.handleMessage('monitor.events', data))
    this.socket.on('monitor.metrics', (data) => this.handleMessage('monitor.metrics', data))
    this.socket.on('monitor.alerts', (data) => this.handleMessage('monitor.alerts', data))
  }

  private onConnected(): void {
    console.log('[MonitoringWS] Connected successfully')
    
    this.updateConnectionStatus({
      connected: true,
      connecting: false,
      error: null,
      lastConnected: new Date(),
      reconnectAttempts: 0,
    })

    // Subscribe to active topics
    this.subscribers.forEach((handlers, topic) => {
      if (handlers.size > 0 && this.socket) {
        this.socket.emit('subscribe', topic)
      }
    })

    // Clear any reconnect timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  private onDisconnected(reason: string): void {
    console.log('[MonitoringWS] Disconnected:', reason)
    
    this.updateConnectionStatus({
      connected: false,
      connecting: false,
      error: `Disconnected: ${reason}`,
    })

    // Attempt reconnection if it wasn't manual
    if (reason !== 'io client disconnect') {
      this.scheduleReconnect()
    }
  }

  private onConnectionError(error: Error): void {
    console.error('[MonitoringWS] Connection error:', error)
    
    this.updateConnectionStatus({
      connected: false,
      connecting: false,
      error: error.message,
    })

    this.scheduleReconnect()
  }

  private onReconnected(): void {
    console.log('[MonitoringWS] Reconnected successfully')
    this.onConnected()
  }

  private onError(error: any): void {
    console.error('[MonitoringWS] Socket error:', error)
    
    this.updateConnectionStatus({
      error: error.message || 'Socket error',
    })
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      return // Already scheduled
    }

    if (this.connectionStatus.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[MonitoringWS] Max reconnection attempts reached')
      this.updateConnectionStatus({
        error: 'Max reconnection attempts reached',
      })
      return
    }

    const attempt = this.connectionStatus.reconnectAttempts + 1
    const delay = Math.min(this.reconnectBaseDelay * Math.pow(2, attempt - 1), 30000) // Max 30 seconds
    
    console.log(`[MonitoringWS] Scheduling reconnect attempt ${attempt} in ${delay}ms`)
    
    this.updateConnectionStatus({ reconnectAttempts: attempt })

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      console.log(`[MonitoringWS] Reconnect attempt ${attempt}...`)
      this.connect().catch(error => {
        console.error(`[MonitoringWS] Reconnect attempt ${attempt} failed:`, error)
      })
    }, delay)
  }

  private handleMessage(topic: MonitoringTopic, data: any): void {
    // Add to throttle queue
    this.eventQueue.push({ topic, data })

    // Start throttle processing if not already running
    if (!this.throttleTimer) {
      this.processThrottleQueue()
    }
  }

  private processThrottleQueue(): void {
    const batchSize = Math.min(this.eventQueue.length, this.throttleOptions.maxBatchSize)
    const batch = this.eventQueue.splice(0, batchSize)

    // Group by topic for efficient processing
    const byTopic = new Map<MonitoringTopic, any[]>()
    batch.forEach(({ topic, data }) => {
      if (!byTopic.has(topic)) {
        byTopic.set(topic, [])
      }
      byTopic.get(topic)!.push(data)
    })

    // Process each topic
    byTopic.forEach((events, topic) => {
      const handlers = this.subscribers.get(topic)
      if (handlers && handlers.size > 0) {
        handlers.forEach(handler => {
          try {
            // For high-volume events, pass the batch
            if (events.length === 1) {
              handler(events[0])
            } else {
              handler({ type: 'batch', events })
            }
          } catch (error) {
            console.error(`[MonitoringWS] Error in ${topic} handler:`, error)
          }
        })
      }
    })

    // Schedule next processing if queue not empty
    if (this.eventQueue.length > 0) {
      const delay = 1000 / this.throttleOptions.maxEventsPerSecond
      this.throttleTimer = setTimeout(() => {
        this.throttleTimer = null
        this.processThrottleQueue()
      }, delay)
    } else {
      this.throttleTimer = null
    }
  }

  private updateConnectionStatus(updates: Partial<WebSocketConnectionStatus>): void {
    this.connectionStatus = { ...this.connectionStatus, ...updates }
    
    // Notify status subscribers
    this.statusSubscribers.forEach(handler => {
      try {
        handler(this.connectionStatus)
      } catch (error) {
        console.error('[MonitoringWS] Error in status handler:', error)
      }
    })
  }
}

// Create and export singleton instance
export const monitoringWebSocket = new MonitoringWebSocketService()

// Export type for dependency injection
export type MonitoringWebSocketServiceType = typeof monitoringWebSocket

export default monitoringWebSocket