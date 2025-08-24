/**
 * AppleStyleIdeaGrid - Grid layout for Apple-style idea cards
 * 
 * This component provides a responsive grid layout for displaying idea cards
 * in an Apple-inspired design with:
 * - Responsive grid that adapts to screen size
 * - Smooth animations and transitions
 * - Proper spacing and alignment
 * - Section headers with counts
 * - Empty states
 */

import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AppleStyleIdeaCard } from './AppleStyleIdeaCard'
import type { FeedItem } from '@/types'

interface AppleStyleIdeaGridProps {
  title: string
  subtitle: string
  items: FeedItem[]
  selectedItem: string | null
  onItemSelect: (item: FeedItem) => void
  onItemAction: (itemId: string, action: string) => void
  isDraggable: boolean
  emptyStateIcon?: string
  emptyStateMessage?: string
}

export const AppleStyleIdeaGrid: React.FC<AppleStyleIdeaGridProps> = ({
  title,
  subtitle,
  items,
  selectedItem,
  onItemSelect,
  onItemAction,
  isDraggable,
  emptyStateIcon = '✨',
  emptyStateMessage = 'No items to display'
}) => {
  if (items.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center py-12"
      >
        <div className="text-4xl mb-4">{emptyStateIcon}</div>
        <h3 className="text-lg font-medium text-white/70 mb-2">{title}</h3>
        <p className="text-sm text-white/50">{emptyStateMessage}</p>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-6"
    >
      {/* Section Header - Apple-style */}
      <div className="flex items-center justify-between mb-2">
        <div>
          <h3 className="text-2xl font-bold text-white mb-1">{title}</h3>
          <p className="text-base text-white/70">{subtitle}</p>
        </div>
        <div className="flex items-center space-x-2">
          <div className="text-sm font-semibold text-white/60 bg-white/10 px-4 py-2 rounded-full backdrop-blur-sm">
            {items.length}
          </div>
        </div>
      </div>

      {/* Grid Container - Apple widget board style */}
      <div className="grid auto-rows-[210px] grid-cols-[repeat(auto-fill,minmax(360px,1fr))] gap-6">
        <AnimatePresence mode="popLayout">
          {items.map((item, index) => (
            <AppleStyleIdeaCard
              key={item.id}
              item={item}
              isSelected={selectedItem === item.id}
              onSelect={() => onItemSelect(item)}
              onAction={onItemAction}
              isDraggable={isDraggable}
              index={index}
            />
          ))}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}

export default AppleStyleIdeaGrid