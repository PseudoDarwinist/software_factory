/**
 * ThinkStage - Enhanced Think stage with intelligent feed management
 * 
 * This component implements the Think stage of the Mission Control workflow:
 * - Intelligent idea categorization and triage
 * - Context panel with graph relationships and historical context
 * - Drag-to-define functionality with visual feedback
 * - Idea dismissal and escalation features
 * - Real-time updates via WebSocket integration
 * 
 * Requirements addressed:
 * - Requirement 2: Intelligent Idea Capture and Context-Aware Triage
 * - Requirement 10: Graph-Based Relationship Navigation and Discovery
 * 
 * The component provides a sophisticated feed management experience that helps
 * users quickly identify and act on the most important ideas and issues.
 */

import React, { useState, useMemo, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useDrag } from 'react-dnd'
import { clsx } from 'clsx'
import { LiquidCard } from '@/components/core/LiquidCard'

import { SpecWorkflowEditor } from './SpecWorkflowEditor'
import type { FeedItem, SDLCStage } from '@/types'

interface ThinkStageProps {
  feedItems: FeedItem[]
  selectedProject: string | null
  selectedFeedItem: string | null
  onFeedItemSelect: (feedItemId: string | null) => void
  onFeedItemAction: (feedItemId: string, action: string) => void
  onStageChange: (stage: SDLCStage) => void
  loading: boolean
  error: string | null
}

type FilterType = 'all' | 'unread' | 'high' | 'medium' | 'low' | 'ideas' | 'alerts'
type SortType = 'priority' | 'recent' | 'alphabetical'

interface CategoryStats {
  total: number
  unread: number
  high: number
  medium: number
  low: number
  ideas: number
  alerts: number
}

export const ThinkStage: React.FC<ThinkStageProps> = ({
  feedItems,
  selectedProject,
  selectedFeedItem,
  onFeedItemSelect,
  onFeedItemAction,
  onStageChange,
  loading,
  error,
}) => {
  const [filter, setFilter] = useState<FilterType>('all')
  const [sortBy, setSortBy] = useState<SortType>('priority')
  const [hoveredItem, setHoveredItem] = useState<string | null>(null)
  const [showContextPanel, setShowContextPanel] = useState(false)
  const [contextData, setContextData] = useState<any>(null)
  const [showSpecEditor, setShowSpecEditor] = useState(false)
  const [selectedFeedItemForSpec, setSelectedFeedItemForSpec] = useState<FeedItem | null>(null)

  // Filter and categorize feed items
  const { processedItems, categoryStats } = useMemo(() => {
    let filtered = feedItems

    // Filter by project if selected
    if (selectedProject) {
      filtered = filtered.filter(item => item.projectId === selectedProject)
    }

    // Only show items that are in Think stage or have no stage assigned
    filtered = filtered.filter(item => 
      !item.metadata?.stage || item.metadata.stage === 'think'
    )

    // Apply category filters
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
      case 'ideas':
        filtered = filtered.filter(item => item.kind === 'idea')
        break
      case 'alerts':
        filtered = filtered.filter(item => item.kind !== 'idea')
        break
    }

    // Sort items
    const sorted = [...filtered].sort((a, b) => {
      switch (sortBy) {
        case 'priority':
          const priorityOrder = { red: 3, amber: 2, info: 1 }
          const priorityDiff = priorityOrder[b.severity] - priorityOrder[a.severity]
          if (priorityDiff !== 0) return priorityDiff
          return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
        
        case 'recent':
          return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
        
        case 'alphabetical':
          return a.title.localeCompare(b.title)
        
        default:
          return 0
      }
    })

    // Calculate category statistics
    const stats: CategoryStats = {
      total: feedItems.length,
      unread: feedItems.filter(item => item.unread).length,
      high: feedItems.filter(item => item.severity === 'red').length,
      medium: feedItems.filter(item => item.severity === 'amber').length,
      low: feedItems.filter(item => item.severity === 'info').length,
      ideas: feedItems.filter(item => item.kind === 'idea').length,
      alerts: feedItems.filter(item => item.kind !== 'idea').length,
    }

    return { processedItems: sorted, categoryStats: stats }
  }, [feedItems, selectedProject, filter, sortBy])

  // Separate ideas from alerts for better organization
  const { ideas, alerts } = useMemo(() => {
    const ideaItems = processedItems.filter(item => item.kind === 'idea')
    const alertItems = processedItems.filter(item => item.kind !== 'idea')
    return { ideas: ideaItems, alerts: alertItems }
  }, [processedItems])

  // Handle item selection and context loading
  const handleItemSelect = useCallback((item: FeedItem) => {
    if (selectedFeedItem === item.id) {
      onFeedItemSelect(null)
      setShowContextPanel(false)
      setContextData(null)
    } else {
      onFeedItemSelect(item.id)
      setShowContextPanel(true)
      loadContextData(item)
    }
  }, [selectedFeedItem, onFeedItemSelect])

  // Load context data for selected item
  const loadContextData = useCallback(async (item: FeedItem) => {
    try {
      // Simulate loading context data - in real implementation this would
      // call the graph service and vector context service
      const mockContext = {
        relatedItems: feedItems.filter(f => 
          f.id !== item.id && 
          f.projectId === item.projectId &&
          (f.title.toLowerCase().includes(item.title.toLowerCase().split(' ')[0]) ||
           f.summary?.toLowerCase().includes(item.title.toLowerCase().split(' ')[0]))
        ).slice(0, 3),
        historicalContext: [
          { type: 'similar_spec', title: 'Similar feature implemented in Q2', confidence: 0.85 },
          { type: 'team_expertise', title: 'John has worked on related features', confidence: 0.92 },
          { type: 'code_reference', title: 'Related code in user-management module', confidence: 0.78 }
        ],
        graphRelationships: {
          connectedCommits: 2,
          relatedSpecs: 1,
          teamMembers: 3
        }
      }
      
      setContextData(mockContext)
    } catch (error) {
      console.error('Failed to load context data:', error)
      setContextData(null)
    }
  }, [feedItems])

  // Handle item actions
  const handleItemAction = useCallback(async (itemId: string, action: string) => {
    try {
      if (action === 'create_spec') {
        const feedItem = feedItems.find(item => item.id === itemId)
        if (feedItem) {
          setSelectedFeedItemForSpec(feedItem)
          setShowSpecEditor(true)
        }
        return
      }
      
      await onFeedItemAction(itemId, action)
      
      // If dismissing, remove from selection
      if (action === 'dismiss' && selectedFeedItem === itemId) {
        onFeedItemSelect(null)
        setShowContextPanel(false)
        setContextData(null)
      }
    } catch (error) {
      console.error('Failed to perform item action:', error)
    }
  }, [onFeedItemAction, selectedFeedItem, onFeedItemSelect, feedItems])

  const closeSpecEditor = () => {
    setShowSpecEditor(false)
    setSelectedFeedItemForSpec(null)
  }

  const handlePhaseComplete = (phase: string) => {
    console.log('Phase completed:', phase)
    if (phase === 'all') {
      // All phases completed, close editor and move item to Define stage
      closeSpecEditor()
      // Optionally trigger a stage change or refresh
    }
  }

  return (
    <div className="h-full flex">
      {/* Main Feed Column */}
      <div className="flex-1 flex flex-col">
        {/* Header with filters and controls */}
        <div className="flex items-center justify-between p-4 border-b border-white/10">
          <div className="flex items-center space-x-4">
            <h2 className="text-lg font-semibold text-white">Think</h2>
            
            {/* Category filters */}
            <div className="flex items-center space-x-2">
              {([
                { type: 'all', label: 'All', count: categoryStats.total },
                { type: 'unread', label: 'Unread', count: categoryStats.unread },
                { type: 'ideas', label: 'Ideas', count: categoryStats.ideas },
                { type: 'alerts', label: 'Alerts', count: categoryStats.alerts },
                { type: 'high', label: 'High', count: categoryStats.high },
                { type: 'medium', label: 'Medium', count: categoryStats.medium },
              ] as const).map(({ type, label, count }) => (
                <FilterButton
                  key={type}
                  type={type}
                  label={label}
                  count={count}
                  isActive={filter === type}
                  onClick={() => setFilter(type)}
                />
              ))}
            </div>
          </div>

          {/* Sort and view controls */}
          <div className="flex items-center space-x-3">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortType)}
              className="bg-white/10 border border-white/20 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            >
              <option value="priority">Priority</option>
              <option value="recent">Recent</option>
              <option value="alphabetical">A-Z</option>
            </select>

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
              {/* Ideas Section */}
              {ideas.length > 0 && (
                <FeedSection
                  title="Untriaged Ideas"
                  subtitle="Ideas ready to be promoted to Define"
                  items={ideas}
                  selectedItem={selectedFeedItem}
                  hoveredItem={hoveredItem}
                  onItemSelect={handleItemSelect}
                  onItemHover={setHoveredItem}
                  onItemAction={handleItemAction}
                  isDraggable={true}
                />
              )}

              {/* Alerts Section */}
              {alerts.length > 0 && (
                <FeedSection
                  title="Needs Attention"
                  subtitle="Issues and updates requiring decisions"
                  items={alerts}
                  selectedItem={selectedFeedItem}
                  hoveredItem={hoveredItem}
                  onItemSelect={handleItemSelect}
                  onItemHover={setHoveredItem}
                  onItemAction={handleItemAction}
                  isDraggable={false}
                />
              )}

              {/* Empty state */}
              {processedItems.length === 0 && (
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

      {/* Context Panel */}
      <AnimatePresence>
        {showContextPanel && selectedFeedItem && contextData && (
          <motion.div
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="w-80 bg-black/20 backdrop-blur-md border-l border-white/10 flex flex-col"
          >
            <ContextPanel
              selectedItem={feedItems.find(item => item.id === selectedFeedItem)!}
              contextData={contextData}
              onClose={() => {
                setShowContextPanel(false)
                setContextData(null)
                onFeedItemSelect(null)
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Specification Editor */}
      <AnimatePresence>
        {showSpecEditor && selectedFeedItemForSpec && selectedProject && (
          <SpecWorkflowEditor
            feedItem={selectedFeedItemForSpec}
            projectId={selectedProject}
            onComplete={closeSpecEditor}
            onClose={closeSpecEditor}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

// Filter Button Component
interface FilterButtonProps {
  type: FilterType
  label: string
  count: number
  isActive: boolean
  onClick: () => void
}

const FilterButton: React.FC<FilterButtonProps> = ({ type, label, count, isActive, onClick }) => {
  const getFilterColor = () => {
    switch (type) {
      case 'high': return 'text-red-400 border-red-500/50'
      case 'medium': return 'text-amber-400 border-amber-500/50'
      case 'low': return 'text-gray-400 border-gray-500/50'
      case 'ideas': return 'text-blue-400 border-blue-500/50'
      case 'alerts': return 'text-orange-400 border-orange-500/50'
      default: return 'text-white border-white/30'
    }
  }

  return (
    <motion.button
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onClick={onClick}
      className={clsx(
        'flex items-center space-x-1 px-3 py-1.5 rounded-full text-xs transition-all',
        isActive
          ? `bg-white/20 border ${getFilterColor()}`
          : 'bg-white/5 text-white/70 hover:bg-white/10 hover:text-white/90 border border-transparent'
      )}
    >
      <span>{label}</span>
      {count > 0 && (
        <div className="bg-white/30 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
          {count > 99 ? '99+' : count}
        </div>
      )}
    </motion.button>
  )
}

// Feed Section Component
interface FeedSectionProps {
  title: string
  subtitle: string
  items: FeedItem[]
  selectedItem: string | null
  hoveredItem: string | null
  onItemSelect: (item: FeedItem) => void
  onItemHover: (itemId: string | null) => void
  onItemAction: (itemId: string, action: string) => void
  isDraggable: boolean
}

const FeedSection: React.FC<FeedSectionProps> = ({
  title,
  subtitle,
  items,
  selectedItem,
  hoveredItem,
  onItemSelect,
  onItemHover,
  onItemAction,
  isDraggable,
}) => {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium text-white/80">{title}</h3>
          <p className="text-xs text-white/60">{subtitle}</p>
        </div>
        <div className="text-xs text-white/50 bg-white/10 px-2 py-1 rounded-full">
          {items.length}
        </div>
      </div>
      
      <div className="space-y-2">
        {items.map((item, index) => (
          <FeedItemCard
            key={item.id}
            item={item}
            isSelected={selectedItem === item.id}
            isHovered={hoveredItem === item.id}
            onSelect={() => onItemSelect(item)}
            onHover={onItemHover}
            onAction={onItemAction}
            isDraggable={isDraggable}
            index={index}
          />
        ))}
      </div>
    </div>
  )
}

// Feed Item Card Component
interface FeedItemCardProps {
  item: FeedItem
  isSelected: boolean
  isHovered: boolean
  onSelect: () => void
  onHover: (itemId: string | null) => void
  onAction: (itemId: string, action: string) => void
  isDraggable: boolean
  index: number
}

const FeedItemCard: React.FC<FeedItemCardProps> = ({
  item,
  isSelected,
  isHovered,
  onSelect,
  onHover,
  onAction,
  isDraggable,
  index,
}) => {
  const [{ isDragging }, drag] = useDrag(() => ({
    type: 'FEED_ITEM',
    item: { id: item.id, type: item.kind },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
    canDrag: isDraggable,
  }))

  const getItemIcon = () => {
    switch (item.kind) {
      case 'idea': return '💭'
      case 'ci_fail': return '🚨'
      case 'pr_review': return '👀'
      case 'spec_change': return '📝'
      case 'qa_blocker': return '🛑'
      case 'agent_suggestion': return '🤖'
      case 'deployment': return '🚀'
      case 'merge': return '🔀'
      default: return '📋'
    }
  }

  const getItemLabel = () => {
    switch (item.kind) {
      case 'idea': return 'Idea'
      case 'ci_fail': return 'CI Failed'
      case 'pr_review': return 'PR Review'
      case 'spec_change': return 'Spec Updated'
      case 'qa_blocker': return 'QA Blocker'
      case 'agent_suggestion': return 'AI Suggestion'
      case 'deployment': return 'Deployment'
      case 'merge': return 'Merged'
      default: return 'Update'
    }
  }

  return (
    <motion.div
      ref={isDraggable ? drag : undefined}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: isDragging ? 0.5 : 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      onMouseEnter={() => onHover(item.id)}
      onMouseLeave={() => onHover(null)}
      className={clsx(
        'relative',
        isDraggable && 'cursor-move',
        isDragging && 'scale-105 rotate-2'
      )}
    >
      <LiquidCard
        variant="feed"
        severity={item.severity}
        urgency={item.severity === 'red' ? 'high' : item.severity === 'amber' ? 'medium' : 'low'}
        onClick={onSelect}
        className={clsx(
          'transition-all',
          isSelected && 'ring-2 ring-blue-500/50',
          item.unread && 'border-l-4 border-l-blue-500'
        )}
      >
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-white/10 flex items-center justify-center">
            <span className="text-sm">{getItemIcon()}</span>
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-2 mb-1">
              <span className="text-xs text-white/60 bg-white/10 px-2 py-1 rounded-full">
                {getItemLabel()}
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
              
              {/* Action buttons */}
              <div className="flex items-center space-x-1">
                <div className="text-xs text-green-400 font-semibold"
                  style={{
                    color: '#10b981',
                    textShadow: '0 0 8px rgba(16, 185, 129, 0.8), 0 0 16px rgba(16, 185, 129, 0.4)',
                    fontWeight: '600',
                    letterSpacing: '0.025em'
                  }}>
                  Drag to Define →
                </div>
                
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onAction(item.id, 'dismiss')
                  }}
                  className="text-xs text-white/50 hover:text-white/80 px-2 py-1 rounded hover:bg-white/10"
                >
                  Dismiss
                </button>
                
                {item.severity !== 'red' && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onAction(item.id, 'escalate')
                    }}
                    className="text-xs text-white/50 hover:text-white/80 px-2 py-1 rounded hover:bg-white/10"
                  >
                    Escalate
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </LiquidCard>
    </motion.div>
  )
}

// Context Panel Component
interface ContextPanelProps {
  selectedItem: FeedItem
  contextData: any
  onClose: () => void
}

const ContextPanel: React.FC<ContextPanelProps> = ({
  selectedItem,
  contextData,
  onClose,
}) => {
  return (
    <>
      {/* Header */}
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">Context</h3>
          <button
            onClick={onClose}
            className="text-white/60 hover:text-white/80 p-1"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <p className="text-sm text-white/70 mt-1">
          {selectedItem.title}
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Related Items */}
        {contextData.relatedItems?.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-white/80 mb-3">Related Items</h4>
            <div className="space-y-2">
              {contextData.relatedItems.map((item: FeedItem) => (
                <div key={item.id} className="bg-white/5 rounded-lg p-3">
                  <h5 className="text-sm font-medium text-white">{item.title}</h5>
                  <p className="text-xs text-white/60 mt-1">{item.summary}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Historical Context */}
        {contextData.historicalContext?.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-white/80 mb-3">Historical Context</h4>
            <div className="space-y-2">
              {contextData.historicalContext.map((context: any, index: number) => (
                <div key={index} className="bg-white/5 rounded-lg p-3">
                  <div className="flex items-center justify-between">
                    <h5 className="text-sm font-medium text-white">{context.title}</h5>
                    <div className="text-xs text-green-400">
                      {Math.round(context.confidence * 100)}%
                    </div>
                  </div>
                  <p className="text-xs text-white/60 mt-1 capitalize">{context.type.replace('_', ' ')}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Graph Relationships */}
        {contextData.graphRelationships && (
          <div>
            <h4 className="text-sm font-medium text-white/80 mb-3">Connections</h4>
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-white/5 rounded-lg p-3 text-center">
                <div className="text-lg font-bold text-white">
                  {contextData.graphRelationships.connectedCommits}
                </div>
                <div className="text-xs text-white/60">Commits</div>
              </div>
              <div className="bg-white/5 rounded-lg p-3 text-center">
                <div className="text-lg font-bold text-white">
                  {contextData.graphRelationships.relatedSpecs}
                </div>
                <div className="text-xs text-white/60">Specs</div>
              </div>
              <div className="bg-white/5 rounded-lg p-3 text-center">
                <div className="text-lg font-bold text-white">
                  {contextData.graphRelationships.teamMembers}
                </div>
                <div className="text-xs text-white/60">People</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  )
}

export default ThinkStage