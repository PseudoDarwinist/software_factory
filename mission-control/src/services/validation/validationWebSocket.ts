/**
 * Validation WebSocket Service
 * - Handles real-time events for Validate phase (checks, runs, evidence)
 * - Provides connection management with auto-reconnect and throttling
 * - Mirrors the monitoring websocket service patterns
 */

import { io, Socket } from 'socket.io-client'
import type { ValidationCheck, ValidationRun } from '@/types/validation'

export type ValidationTopic =
  | 'validation.checks' // stream of individual check updates
  | 'validation.runs' // run-level lifecycle events
  | 'validation.evidence' // evidence appended/updated
  | 'phase.transition' // cross-stage transition events

export interface WebSocketConnectionStatus {
  connected: boolean
  connecting: boolean
  error: string | null
  lastConnected: Date | null
  reconnectAttempts: number
}

export interface ThrottleOptions {
  maxEventsPerSecond: number
  maxBatchSize: number
}

type TopicPayload = ValidationCheck | ValidationRun | any
type EventHandler = (data: TopicPayload) => void

class ValidationWebSocketService {
  private socket: Socket | null = null
  private status: WebSocketConnectionStatus = {
    connected: false,
    connecting: false,
    error: null,
    lastConnected: null,
    reconnectAttempts: 0,
  }

  private subscribers: Map<ValidationTopic, Set<EventHandler>> = new Map()
  private statusSubscribers: Set<(s: WebSocketConnectionStatus) => void> = new Set()

  private eventQueue: Array<{ topic: ValidationTopic; data: TopicPayload }> = []
  private throttleTimer: NodeJS.Timeout | null = null
  private throttle: ThrottleOptions = { maxEventsPerSecond: 60, maxBatchSize: 30 }

  private reconnectTimer: NodeJS.Timeout | null = null
  private maxReconnectAttempts = 10
  private reconnectBaseDelay = 1000

  constructor() {
    ;(['validation.checks', 'validation.runs', 'validation.evidence', 'phase.transition'] as ValidationTopic[]).forEach((t) =>
      this.subscribers.set(t, new Set())
    )
  }

  async connect(): Promise<void> {
    if (this.socket?.connected || this.status.connecting) return
    this.updateStatus({ connecting: true, error: null })

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const socketUrl = `${protocol}//${host}`

    this.socket = io(socketUrl, {
      transports: ['websocket'],
      timeout: 10000,
      forceNew: true,
      auth: { token: localStorage.getItem('auth_token') || undefined },
    })

    this.setupHandlers()

    await new Promise<void>((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('Connection timeout')), 10000)
      this.socket!.once('connect', () => {
        clearTimeout(timeout)
        this.onConnected()
        resolve()
      })
      this.socket!.once('connect_error', (err) => {
        clearTimeout(timeout)
        this.onConnectionError(err)
        reject(err)
      })
    })
  }

  disconnect(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer)
    if (this.throttleTimer) clearTimeout(this.throttleTimer)
    this.reconnectTimer = null
    this.throttleTimer = null

    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
    }
    this.updateStatus({ connected: false, connecting: false, error: null, reconnectAttempts: 0 })
  }

  subscribe(topic: ValidationTopic, handler: EventHandler): () => void {
    const set = this.subscribers.get(topic)
    if (!set) return () => {}
    set.add(handler)
    if (this.socket?.connected) this.socket.emit('subscribe', topic)
    return () => {
      set.delete(handler)
      if (set.size === 0 && this.socket?.connected) this.socket.emit('unsubscribe', topic)
    }
  }

  onStatusChange(handler: (s: WebSocketConnectionStatus) => void): () => void {
    this.statusSubscribers.add(handler)
    handler(this.status)
    return () => this.statusSubscribers.delete(handler)
  }

  setThrottle(options: Partial<ThrottleOptions>): void {
    this.throttle = { ...this.throttle, ...options }
  }

  private setupHandlers(): void {
    if (!this.socket) return
    this.socket.on('connect', this.onConnected.bind(this))
    this.socket.on('disconnect', this.onDisconnected.bind(this))
    this.socket.on('connect_error', this.onConnectionError.bind(this))

    this.socket.on('validation.checks', (d) => this.enqueue('validation.checks', d))
    this.socket.on('validation.runs', (d) => this.enqueue('validation.runs', d))
    // Some backends emit underscore variant; mirror it to dot-style
    this.socket.on('phase_transition', (d) => this.enqueue('phase.transition', d as any))
    this.socket.on('validation.evidence', (d) => this.enqueue('validation.evidence', d))
    // Cross-stage transition
    this.socket.on('phase.transition', (d) => this.enqueue('phase.transition', d))
  }

  private onConnected(): void {
    this.updateStatus({ connected: true, connecting: false, error: null, lastConnected: new Date(), reconnectAttempts: 0 })
    // Re-subscribe to active topics
    this.subscribers.forEach((handlers, topic) => {
      if (handlers.size > 0) this.socket?.emit('subscribe', topic)
    })
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  private onDisconnected(reason: string): void {
    this.updateStatus({ connected: false, connecting: false, error: `Disconnected: ${reason}` })
    if (reason !== 'io client disconnect') this.scheduleReconnect()
  }

  private onConnectionError(error: Error): void {
    this.updateStatus({ connected: false, connecting: false, error: error.message })
    this.scheduleReconnect()
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return
    if (this.status.reconnectAttempts >= this.maxReconnectAttempts) {
      this.updateStatus({ error: 'Max reconnection attempts reached' })
      return
    }
    const attempt = this.status.reconnectAttempts + 1
    const delay = Math.min(this.reconnectBaseDelay * Math.pow(2, attempt - 1), 30000)
    this.updateStatus({ reconnectAttempts: attempt })
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.connect().catch(() => {})
    }, delay)
  }

  private enqueue(topic: ValidationTopic, data: TopicPayload): void {
    this.eventQueue.push({ topic, data })
    if (!this.throttleTimer) this.processQueue()
  }

  private processQueue(): void {
    const batchSize = Math.min(this.eventQueue.length, this.throttle.maxBatchSize)
    const batch = this.eventQueue.splice(0, batchSize)

    const grouped = new Map<ValidationTopic, TopicPayload[]>()
    batch.forEach(({ topic, data }) => {
      if (!grouped.has(topic)) grouped.set(topic, [])
      grouped.get(topic)!.push(data)
    })

    grouped.forEach((events, topic) => {
      const handlers = this.subscribers.get(topic)
      if (!handlers || handlers.size === 0) return
      handlers.forEach((handler) => {
        if (events.length === 1) handler(events[0])
        else handler({ type: 'batch', events })
      })
    })

    if (this.eventQueue.length > 0) {
      const delay = 1000 / this.throttle.maxEventsPerSecond
      this.throttleTimer = setTimeout(() => {
        this.throttleTimer = null
        this.processQueue()
      }, delay)
    } else {
      this.throttleTimer = null
    }
  }

  private updateStatus(updates: Partial<WebSocketConnectionStatus>): void {
    this.status = { ...this.status, ...updates }
    this.statusSubscribers.forEach((h) => {
      try {
        h(this.status)
      } catch (e) {
        console.error('[ValidationWS] Status handler error:', e)
      }
    })
  }
}

export const validationWebSocket = new ValidationWebSocketService()
export type ValidationWebSocketServiceType = typeof validationWebSocket
export default validationWebSocket

