/**
 * FeedColumn - Center column showing decision feed and untriaged thoughts
 * 
 * This component displays the heart of Mission Control - the feed of items
 * that need human attention. It includes:
 * - Untriaged thoughts that can be dragged to Define
 * - Alert cards for issues requiring decisions
 * - Magnetic field interactions between related items
 * - Organic card morphing based on content type
 * 
 * Why this component exists:
 * - Central hub for all items requiring human decision
 * - Implements drag-and-drop workflow for idea progression
 * - Provides quick actions for common tasks
 * - Maintains focus on what matters most
 * 
 * For AI agents: This is the main decision feed.
 * Items are categorized and prioritized for human attention.
 */

import React, { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useDrag } from 'react-dnd'
import { clsx } from 'clsx'
import { LiquidCard } from '@/components/core/LiquidCard'
import { tokens } from '@/styles/tokens'
import type { FeedItem, SDLCStage } from '@/types'

interface FeedColumnProps {
  feedItems: FeedItem[]
  selectedFeedItem: string | null
  onFeedItemSelect: (feedItemId: string | null) => void
  onFeedItemAction: (feedItemId: string, action: string) => void
  selectedProject: string | null
  loading: boolean
  error: string | null
  activeStage: SDLCStage
  onStageChange: (stage: SDLCStage) => void
}

export const FeedColumn: React.FC<FeedColumnProps> = ({
  feedItems,
  selectedFeedItem,
  onFeedItemSelect,
  onFeedItemAction,
  selectedProject,
  loading,
  error,
  activeStage,
  onStageChange,
}) => {
  const [filter, setFilter] = useState<'all' | 'unread' | 'high' | 'medium' | 'low'>('all')
  const [hoveredItem, setHoveredItem] = useState<string | null>(null)

  // Filter and sort feed items
  const processedFeedItems = useMemo(() => {
    let filtered = feedItems

    // Filter by project if selected
    if (selectedProject) {
      filtered = filtered.filter(item => item.projectId === selectedProject)
    }

    // Apply additional filters
    switch (filter) {
      case 'unread':
        filtered = filtered.filter(item => item.unread)
        break
      case 'high':
        filtered = filtered.filter(item => item.severity === 'red')
        break
      case 'medium':
        filtered = filtered.filter(item => item.severity === 'amber')
        break
      case 'low':
        filtered = filtered.filter(item => item.severity === 'info')
        break
    }

    // Sort by priority and recency
    return filtered.sort((a, b) => {
      const priorityOrder = { red: 3, amber: 2, info: 1 }
      const priorityDiff = priorityOrder[b.severity] - priorityOrder[a.severity]
      
      if (priorityDiff !== 0) return priorityDiff
      
      return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    })
  }, [feedItems, selectedProject, filter])

  // Separate untriaged thoughts from other items based on stage
  const untriagedItems = processedFeedItems.filter(item => 
    item.kind === 'idea' && (!item.metadata?.stage || item.metadata.stage === 'think')
  )
  const alertItems = processedFeedItems.filter(item => 
    item.kind !== 'idea' || (item.metadata?.stage && item.metadata.stage !== 'think')
  )

  const handleItemSelect = (item: FeedItem) => {
    if (selectedFeedItem === item.id) {
      onFeedItemSelect(null)
    } else {
      onFeedItemSelect(item.id)
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header with filters */}
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        <div className="flex items-center space-x-4">
          <h2 className="text-lg font-semibold text-white">Feed</h2>
          
          {/* Filter buttons */}
          <div className="flex items-center space-x-2">
            {(['all', 'unread', 'high', 'medium', 'low'] as const).map((filterType) => (
              <FilterButton
                key={filterType}
                type={filterType}
                isActive={filter === filterType}
                onClick={() => setFilter(filterType)}
                count={filterType === 'all' ? processedFeedItems.length : 
                       filterType === 'unread' ? processedFeedItems.filter(i => i.unread).length :
                       filterType === 'high' ? processedFeedItems.filter(i => i.severity === 'red').length :
                       filterType === 'medium' ? processedFeedItems.filter(i => i.severity === 'amber').length :
                       processedFeedItems.filter(i => i.severity === 'info').length}
              />
            ))}
          </div>
        </div>

        {/* Refresh button */}
        <motion.button
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => window.location.reload()}
          className="p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors"
          aria-label="Refresh feed"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </motion.button>
      </div>

      {/* Feed content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {loading && (
          <div className="space-y-3">
            {[...Array(8)].map((_, i) => (
              <div
                key={i}
                className="h-20 bg-white/5 rounded-lg animate-pulse"
                style={{ animationDelay: `${i * 0.1}s` }}
              />
            ))}
          </div>
        )}

        {error && (
          <div className="text-center py-8">
            <div className="text-red-400 text-sm mb-2">Failed to load feed</div>
            <button
              onClick={() => window.location.reload()}
              className="text-xs text-white/60 hover:text-white/80"
            >
              Try again
            </button>
          </div>
        )}

        {!loading && !error && (
          <>
            {/* Untriaged Thoughts Section */}
            {untriagedItems.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <h3 className="text-sm font-medium text-white/80">Untriaged thoughts</h3>
                  <div className="text-xs text-white/50 bg-white/10 px-2 py-1 rounded-full">
                    {untriagedItems.length}
                  </div>
                </div>
                
                <div className="space-y-2">
                  {untriagedItems.map((item, index) => (
                    <UntrigedThoughtCard
                      key={item.id}
                      item={item}
                      isSelected={selectedFeedItem === item.id}
                      isHovered={hoveredItem === item.id}
                      onSelect={() => handleItemSelect(item)}
                      onHover={setHoveredItem}
                      onAction={onFeedItemAction}
                      index={index}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Alert Items Section */}
            {alertItems.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <h3 className="text-sm font-medium text-white/80">Needs attention</h3>
                  <div className="text-xs text-white/50 bg-white/10 px-2 py-1 rounded-full">
                    {alertItems.length}
                  </div>
                </div>
                
                <div className="space-y-2">
                  {alertItems.map((item, index) => (
                    <AlertCard
                      key={item.id}
                      item={item}
                      isSelected={selectedFeedItem === item.id}
                      isHovered={hoveredItem === item.id}
                      onSelect={() => handleItemSelect(item)}
                      onHover={setHoveredItem}
                      onAction={onFeedItemAction}
                      index={index}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Empty state */}
            {processedFeedItems.length === 0 && (
              <div className="text-center py-12">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-white/5 flex items-center justify-center">
                  <svg className="w-8 h-8 text-white/40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-white/80 mb-2">All caught up!</h3>
                <p className="text-sm text-white/60">
                  {selectedProject ? 'No items need attention for this project' : 'No items need attention right now'}
                </p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

interface FilterButtonProps {
  type: 'all' | 'unread' | 'high' | 'medium' | 'low'
  isActive: boolean
  onClick: () => void
  count: number
}

const FilterButton: React.FC<FilterButtonProps> = ({ type, isActive, onClick, count }) => {
  const getFilterConfig = () => {
    switch (type) {
      case 'all':
        return { label: 'All', color: 'white' }
      case 'unread':
        return { label: 'Unread', color: 'blue' }
      case 'high':
        return { label: 'High', color: 'red' }
      case 'medium':
        return { label: 'Medium', color: 'amber' }
      case 'low':
        return { label: 'Low', color: 'gray' }
    }
  }

  const config = getFilterConfig()

  return (
    <motion.button
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onClick={onClick}
      className={clsx(
        'flex items-center space-x-1 px-3 py-1.5 rounded-full text-xs transition-all',
        isActive
          ? 'bg-white/20 text-white border border-white/30'
          : 'bg-white/5 text-white/70 hover:bg-white/10 hover:text-white/90'
      )}
    >
      <span>{config.label}</span>
      {count > 0 && (
        <div className="bg-white/30 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
          {count > 99 ? '99+' : count}
        </div>
      )}
    </motion.button>
  )
}

interface UntrigedThoughtCardProps {
  item: FeedItem
  isSelected: boolean
  isHovered: boolean
  onSelect: () => void
  onHover: (itemId: string | null) => void
  onAction: (itemId: string, action: string) => void
  index: number
}

const UntrigedThoughtCard: React.FC<UntrigedThoughtCardProps> = ({
  item,
  isSelected,
  isHovered,
  onSelect,
  onHover,
  onAction,
  index,
}) => {
  const [{ isDragging }, drag] = useDrag(() => ({
    type: 'FEED_ITEM',
    item: { id: item.id, type: 'idea' },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  }))

  return (
    <motion.div
      ref={drag}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: isDragging ? 0.5 : 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      onMouseEnter={() => onHover(item.id)}
      onMouseLeave={() => onHover(null)}
    >
      <LiquidCard
        variant="feed"
        severity="info"
        urgency="low"
        onClick={onSelect}
        className={clsx(
          'cursor-move transition-all',
          isSelected && 'ring-2 ring-blue-500/50',
          isDragging && 'scale-105 rotate-2'
        )}
      >
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center">
            <span className="text-blue-400 text-sm">💭</span>
          </div>
          
          <div className="flex-1 min-w-0">
            <h4 className="font-medium text-white text-sm leading-tight">
              {item.title}
            </h4>
            {item.summary && (
              <p className="text-xs text-white/70 mt-1 line-clamp-2">
                {item.summary}
              </p>
            )}
            <div className="flex items-center justify-between mt-2">
              <div className="text-xs text-white/50">
                {item.actor} · {new Date(item.createdAt).toLocaleDateString()}
              </div>
              <div className={clsx(
                "text-xs",
                item.metadata?.stage 
                  ? "text-blue-400 bg-blue-500/20 px-2 py-1 rounded-full" 
                  : "text-green-400 font-semibold"
              )}
              style={!item.metadata?.stage ? {
                color: '#10b981',
                textShadow: '0 0 8px rgba(16, 185, 129, 0.8), 0 0 16px rgba(16, 185, 129, 0.4)',
                fontWeight: '600',
                letterSpacing: '0.025em'
              } : undefined}>
                {item.metadata?.stage ? `In ${item.metadata.stage}` : 'Drag to Define →'}
              </div>
            </div>
          </div>
        </div>
      </LiquidCard>
    </motion.div>
  )
}

interface AlertCardProps {
  item: FeedItem
  isSelected: boolean
  isHovered: boolean
  onSelect: () => void
  onHover: (itemId: string | null) => void
  onAction: (itemId: string, action: string) => void
  index: number
}

const AlertCard: React.FC<AlertCardProps> = ({
  item,
  isSelected,
  isHovered,
  onSelect,
  onHover,
  onAction,
  index,
}) => {
  const getKindConfig = () => {
    switch (item.kind) {
      case 'ci_fail':
        return { icon: '🚨', label: 'CI Failed', color: 'red' }
      case 'pr_review':
        return { icon: '👀', label: 'PR Review', color: 'amber' }
      case 'spec_change':
        return { icon: '📝', label: 'Spec Updated', color: 'blue' }
      case 'qa_blocker':
        return { icon: '🛑', label: 'QA Blocker', color: 'red' }
      case 'agent_suggestion':
        return { icon: '🤖', label: 'AI Suggestion', color: 'green' }
      case 'deployment':
        return { icon: '🚀', label: 'Deployment', color: 'green' }
      case 'merge':
        return { icon: '🔀', label: 'Merged', color: 'green' }
      default:
        return { icon: '📋', label: 'Update', color: 'gray' }
    }
  }

  const config = getKindConfig()

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      onMouseEnter={() => onHover(item.id)}
      onMouseLeave={() => onHover(null)}
    >
      <LiquidCard
        variant="feed"
        severity={item.severity}
        urgency={item.severity === 'red' ? 'high' : item.severity === 'amber' ? 'medium' : 'low'}
        onClick={onSelect}
        className={clsx(
          'transition-all',
          isSelected && 'ring-2 ring-white/50',
          item.unread && 'border-l-4 border-l-blue-500'
        )}
      >
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-white/10 flex items-center justify-center">
            <span className="text-sm">{config.icon}</span>
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2 mb-1">
              <span className="text-xs text-white/60 bg-white/10 px-2 py-1 rounded-full">
                {config.label}
              </span>
              {item.unread && (
                <div className="w-2 h-2 bg-blue-500 rounded-full" />
              )}
            </div>
            
            <h4 className="font-medium text-white text-sm leading-tight">
              {item.title}
            </h4>
            
            {item.summary && (
              <p className="text-xs text-white/70 mt-1 line-clamp-2">
                {item.summary}
              </p>
            )}
            
            <div className="flex items-center justify-between mt-2">
              <div className="text-xs text-white/50">
                {item.actor} · {new Date(item.createdAt).toLocaleDateString()}
              </div>
              
              {/* Quick actions */}
              <div className="flex items-center space-x-1">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onAction(item.id, 'dismiss')
                  }}
                  className="text-xs text-white/50 hover:text-white/80 px-2 py-1 rounded hover:bg-white/10"
                >
                  Dismiss
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onAction(item.id, 'escalate')
                  }}
                  className="text-xs text-white/50 hover:text-white/80 px-2 py-1 rounded hover:bg-white/10"
                >
                  Escalate
                </button>
              </div>
            </div>
          </div>
        </div>
      </LiquidCard>
    </motion.div>
  )
}

export default FeedColumn