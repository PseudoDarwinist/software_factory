/**
 * EventStream Component - Real-time event monitoring interface
 * 
 * This component displays a live feed of all events flowing through the system
 * with filtering, search, and detailed payload inspection capabilities.
 * 
 * Features:
 * - Real-time event stream with auto-scroll
 * - Event filtering by type and source
 * - Search functionality across event content
 * - Event detail modal with payload inspection
 * - Color-coded event types and status indicators
 * 
 * Why this component exists:
 * - Provides real-time visibility into system events
 * - Enables debugging and troubleshooting capabilities
 * - Supports event analysis and pattern recognition
 * 
 * For AI agents: This is the main event stream monitoring component.
 */

import React, { useState, useMemo, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import type { MonitoringEvent, EventSearchParams } from '@/types/monitoring'

interface EventStreamProps {
  events: MonitoringEvent[]
  className?: string
}

interface EventDetailModalProps {
  event: MonitoringEvent | null
  onClose: () => void
}

export const EventStream: React.FC<EventStreamProps> = ({ events, className }) => {
  const [selectedEvent, setSelectedEvent] = useState<MonitoringEvent | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [sourceFilter, setSourceFilter] = useState<string>('')
  const [isAutoScroll, setIsAutoScroll] = useState(true)
  const eventListRef = useRef<HTMLDivElement>(null)

  // Get unique event types and sources for filters
  const { eventTypes, eventSources } = useMemo(() => {
    const types = new Set<string>()
    const sources = new Set<string>()
    
    events.forEach(event => {
      types.add(event.type)
      sources.add(event.source)
    })
    
    return {
      eventTypes: Array.from(types).sort(),
      eventSources: Array.from(sources).sort(),
    }
  }, [events])

  // Filter events based on search and filters
  const filteredEvents = useMemo(() => {
    return events.filter(event => {
      // Search filter
      if (searchQuery) {
        const searchLower = searchQuery.toLowerCase()
        const searchable = [
          event.type,
          event.source,
          event.id,
          JSON.stringify(event.payload),
        ].join(' ').toLowerCase()
        
        if (!searchable.includes(searchLower)) {
          return false
        }
      }

      // Type filter
      if (typeFilter && event.type !== typeFilter) {
        return false
      }

      // Source filter
      if (sourceFilter && event.source !== sourceFilter) {
        return false
      }

      return true
    })
  }, [events, searchQuery, typeFilter, sourceFilter])

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (isAutoScroll && eventListRef.current) {
      const scrollElement = eventListRef.current
      scrollElement.scrollTop = scrollElement.scrollHeight
    }
  }, [filteredEvents, isAutoScroll])

  // Handle scroll to detect if user manually scrolled up
  const handleScroll = () => {
    if (eventListRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = eventListRef.current
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 50
      setIsAutoScroll(isNearBottom)
    }
  }

  const getEventTypeIcon = (type: string) => {
    if (type.includes('error') || type.includes('failed')) return '🚨'
    if (type.includes('success') || type.includes('complete')) return '✅'
    if (type.includes('warning')) return '⚠️'
    if (type.includes('message')) return '💬'
    if (type.includes('agent')) return '🤖'
    if (type.includes('slack')) return '💬'
    if (type.includes('github')) return '🔧'
    if (type.includes('webhook')) return '🔗'
    return '📡'
  }

  const getEventTypeColor = (event: MonitoringEvent) => {
    if (!event.success || event.error) return 'text-red-400 border-red-500/30'
    if (event.type.includes('warning')) return 'text-amber-400 border-amber-500/30'
    return 'text-green-400 border-green-500/30'
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const truncatePayload = (payload: any, maxLength: number = 100) => {
    const str = JSON.stringify(payload, null, 0)
    if (str.length <= maxLength) return str
    return str.substring(0, maxLength) + '...'
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={clsx('bg-grid rounded-xl p-6 border border-white/10 h-96 flex flex-col', className)}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Event Stream</h3>
        <div className="flex items-center space-x-4">
          <div className="text-xs text-white/60">
            {filteredEvents.length} of {events.length} events
          </div>
          <div className={clsx(
            'w-2 h-2 rounded-full',
            events.length > 0 ? 'bg-green-400 animate-pulse' : 'bg-white/40'
          )} />
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center space-x-3 mb-4">
        {/* Search */}
        <div className="flex-1">
          <input
            type="text"
            placeholder="Search events..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className={clsx(
              'w-full px-3 py-1.5 text-sm',
              'bg-white/5 border border-white/20 rounded-lg',
              'text-white placeholder-white/50',
              'focus:outline-none focus:border-white/40',
              'transition-colors'
            )}
          />
        </div>

        {/* Type Filter */}
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className={clsx(
            'px-3 py-1.5 text-sm',
            'bg-white/5 border border-white/20 rounded-lg',
            'text-white',
            'focus:outline-none focus:border-white/40',
            'transition-colors'
          )}
        >
          <option value="">All Types</option>
          {eventTypes.map(type => (
            <option key={type} value={type} className="bg-black">
              {type}
            </option>
          ))}
        </select>

        {/* Source Filter */}
        <select
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          className={clsx(
            'px-3 py-1.5 text-sm',
            'bg-white/5 border border-white/20 rounded-lg',
            'text-white',
            'focus:outline-none focus:border-white/40',
            'transition-colors'
          )}
        >
          <option value="">All Sources</option>
          {eventSources.map(source => (
            <option key={source} value={source} className="bg-black">
              {source}
            </option>
          ))}
        </select>

        {/* Auto-scroll toggle */}
        <button
          onClick={() => setIsAutoScroll(!isAutoScroll)}
          className={clsx(
            'px-3 py-1.5 text-sm rounded-lg transition-colors',
            isAutoScroll
              ? 'bg-green-500/20 text-green-400 border border-green-500/30'
              : 'bg-white/5 text-white/60 border border-white/20 hover:bg-white/10'
          )}
          title={isAutoScroll ? 'Auto-scroll enabled' : 'Auto-scroll disabled'}
        >
          {isAutoScroll ? '⬇️' : '⏸️'}
        </button>
      </div>

      {/* Event List */}
      <div 
        ref={eventListRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto space-y-2 pr-2"
        style={{ scrollBehavior: isAutoScroll ? 'smooth' : 'auto' }}
      >
        <AnimatePresence initial={false}>
          {filteredEvents.length === 0 ? (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center justify-center h-32 text-white/60"
            >
              <div className="text-center">
                <div className="w-8 h-8 mx-auto mb-2 rounded-full bg-white/5 flex items-center justify-center">
                  <span className="text-white/40">🔍</span>
                </div>
                <p className="text-sm">No events found</p>
                <p className="text-xs text-white/40">
                  {events.length === 0 ? 'Waiting for events...' : 'Try adjusting filters'}
                </p>
              </div>
            </motion.div>
          ) : (
            filteredEvents.map((event, index) => (
              <motion.div
                key={`${event.id}-${event.timestamp}`}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.2, delay: index * 0.01 }}
                onClick={() => setSelectedEvent(event)}
                className={clsx(
                  'p-3 rounded-lg border cursor-pointer transition-all duration-200',
                  'bg-white/5 hover:bg-white/10',
                  getEventTypeColor(event),
                  'hover:scale-[1.01]'
                )}
              >
                <div className="flex items-start space-x-3">
                  {/* Event Icon */}
                  <div className="text-sm mt-0.5">
                    {getEventTypeIcon(event.type)}
                  </div>

                  {/* Event Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <h4 className="text-sm font-medium text-white truncate">
                        {event.type}
                      </h4>
                      <span className="text-xs text-white/60 ml-2">
                        {formatTimestamp(event.timestamp)}
                      </span>
                    </div>
                    
                    <div className="flex items-center space-x-2 mt-1">
                      <span className="text-xs text-white/60">
                        {event.source}
                      </span>
                      {event.processingTime && (
                        <span className="text-xs text-white/50">
                          • {event.processingTime}ms
                        </span>
                      )}
                    </div>

                    {/* Payload Preview */}
                    <div className="mt-2 text-xs text-white/50 font-mono">
                      {truncatePayload(event.payload)}
                    </div>
                  </div>

                  {/* Status Indicator */}
                  <div className={clsx(
                    'w-2 h-2 rounded-full flex-shrink-0 mt-1',
                    event.success && !event.error ? 'bg-green-400' : 'bg-red-400'
                  )} />
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>

      {/* Event Detail Modal */}
      <EventDetailModal 
        event={selectedEvent} 
        onClose={() => setSelectedEvent(null)} 
      />
    </motion.div>
  )
}

const EventDetailModal: React.FC<EventDetailModalProps> = ({ event, onClose }) => {
  if (!event) return null

  const formatJson = (obj: any) => {
    try {
      return JSON.stringify(obj, null, 2)
    } catch {
      return String(obj)
    }
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
          className="bg-black/80 backdrop-blur-md border border-white/20 rounded-xl p-6 max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col"
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-4 pb-4 border-b border-white/10">
            <div className="flex items-center space-x-3">
              <span className="text-lg">{event.type.includes('error') ? '🚨' : '📡'}</span>
              <div>
                <h3 className="text-lg font-semibold text-white">{event.type}</h3>
                <p className="text-sm text-white/60">{event.source}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-white/60 hover:text-white transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Event Details */}
          <div className="flex-1 overflow-y-auto space-y-4">
            {/* Metadata */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <h4 className="text-sm font-medium text-white/80 mb-2">Event ID</h4>
                <p className="text-sm font-mono text-white/60 bg-white/5 px-3 py-2 rounded-lg">
                  {event.id}
                </p>
              </div>
              <div>
                <h4 className="text-sm font-medium text-white/80 mb-2">Timestamp</h4>
                <p className="text-sm text-white/60 bg-white/5 px-3 py-2 rounded-lg">
                  {new Date(event.timestamp).toLocaleString()}
                </p>
              </div>
              {event.processingTime && (
                <div>
                  <h4 className="text-sm font-medium text-white/80 mb-2">Processing Time</h4>
                  <p className="text-sm text-white/60 bg-white/5 px-3 py-2 rounded-lg">
                    {event.processingTime}ms
                  </p>
                </div>
              )}
              <div>
                <h4 className="text-sm font-medium text-white/80 mb-2">Status</h4>
                <div className="flex items-center space-x-2">
                  <div className={clsx(
                    'w-2 h-2 rounded-full',
                    event.success && !event.error ? 'bg-green-400' : 'bg-red-400'
                  )} />
                  <span className="text-sm text-white/60">
                    {event.success && !event.error ? 'Success' : 'Error'}
                  </span>
                </div>
              </div>
            </div>

            {/* Error */}
            {event.error && (
              <div>
                <h4 className="text-sm font-medium text-red-400 mb-2">Error</h4>
                <pre className="text-sm text-red-300 bg-red-500/10 border border-red-500/30 px-3 py-2 rounded-lg overflow-x-auto">
                  {event.error}
                </pre>
              </div>
            )}

            {/* Payload */}
            <div>
              <h4 className="text-sm font-medium text-white/80 mb-2">Payload</h4>
              <pre className="text-xs font-mono text-white/60 bg-white/5 border border-white/10 px-3 py-2 rounded-lg overflow-x-auto max-h-64 overflow-y-auto">
                {formatJson(event.payload)}
              </pre>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

export default EventStream