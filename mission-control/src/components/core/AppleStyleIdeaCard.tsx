/**
 * AppleStyleIdeaCard - Clean, minimalist idea cards
 */

import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { useDrag } from 'react-dnd'
import { clsx } from 'clsx'
import type { FeedItem } from '@/types'

interface AppleStyleIdeaCardProps {
  item: FeedItem
  isSelected: boolean
  onSelect: () => void
  onAction: (itemId: string, action: string) => void
  isDraggable: boolean
  index: number
}

// Generate stable gradient from idea ID
function gradientFromId(id: string) {
  let hash = 2166136261
  for (let i = 0; i < id.length; i++) {
    hash ^= id.charCodeAt(i)
    hash += (hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24)
  }
  const h1 = Math.abs(hash) % 360
  const h2 = (h1 + 60) % 360
  
  return {
    base: `linear-gradient(135deg, hsl(${h1} 70% 16% / .85), hsl(${h2} 70% 16% / .85))`,
    a: `hsl(${h1} 85% 60% / .25)`,
    b: `hsl(${h2} 85% 60% / .25)`
  }
}

// Progress ring component
const ProgressRing: React.FC<{ value: number }> = ({ value }) => {
  const r = 16
  const c = 2 * Math.PI * r
  const offset = c * (1 - Math.min(Math.max(value, 0), 1))
  
  return (
    <svg width="36" height="36" viewBox="0 0 42 42" className="text-white/25">
      <circle cx="21" cy="21" r={r} stroke="currentColor" strokeWidth="3" fill="none" />
      <circle 
        cx="21" 
        cy="21" 
        r={r} 
        stroke="url(#grad)" 
        strokeWidth="3" 
        fill="none"
        strokeDasharray={c} 
        strokeDashoffset={offset}
        style={{ filter: "drop-shadow(0 0 6px rgba(255,255,255,.35))" }}
      />
      <defs>
        <linearGradient id="grad" x1="0" x2="1">
          <stop offset="0%" stopColor="#FFE66B" />
          <stop offset="100%" stopColor="#15F1CC" />
        </linearGradient>
      </defs>
    </svg>
  )
}

export const AppleStyleIdeaCard: React.FC<AppleStyleIdeaCardProps> = ({
  item,
  isSelected,
  onSelect,
  onAction,
  isDraggable,
  index,
}) => {
  const [isHovered, setIsHovered] = useState(false)

  // Drag and drop functionality
  const [{ isDragging }, drag] = useDrag(() => ({
    type: 'FEED_ITEM',
    item: { id: item.id, type: item.kind },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
    canDrag: isDraggable,
  }))

  // Remove age calculation - not needed

  // Get gradient for this idea
  const gradient = gradientFromId(item.id)

  // Calculate real PRD progress from specification artifacts
  const calculatePRDProgress = () => {
    const specId = `spec_${item.id}` // Assuming spec_id format based on your system
    const artifacts = item.metadata?.specificationArtifacts || []
    
    if (artifacts.length === 0) {
      return { progress: 0, status: 'Not Started', hasPRD: false, frozen: false }
    }
    
    // Check artifact statuses
    const frozenCount = artifacts.filter(a => a.status === 'frozen').length
    const reviewedCount = artifacts.filter(a => a.status === 'human_reviewed').length
    const draftCount = artifacts.filter(a => a.status === 'ai_draft').length
    const totalArtifacts = artifacts.length
    const expectedArtifacts = 3 // requirements, design, tasks
    
    // All artifacts frozen = 100% complete
    if (frozenCount === totalArtifacts && totalArtifacts === expectedArtifacts) {
      return { progress: 1.0, status: 'PRD Frozen', hasPRD: true, frozen: true }
    }
    
    // All artifacts reviewed = ready to freeze (90%)
    if (reviewedCount === totalArtifacts && totalArtifacts === expectedArtifacts) {
      return { progress: 0.9, status: 'Ready to Freeze', hasPRD: true, frozen: false }
    }
    
    // Has some artifacts = in progress
    if (totalArtifacts > 0) {
      const progressPercent = (draftCount * 0.3 + reviewedCount * 0.6 + frozenCount * 1.0) / expectedArtifacts
      return { 
        progress: Math.min(progressPercent, 0.8), 
        status: 'PRD Draft', 
        hasPRD: true, 
        frozen: false 
      }
    }
    
    return { progress: 0, status: 'Not Started', hasPRD: false, frozen: false }
  }

  const prdData = calculatePRDProgress()
  const prdProgress = prdData.progress
  const hasPRD = prdData.hasPRD
  const prdFrozen = prdData.frozen

  const getTriageStatus = () => prdData.status

  // Risk shadow
  const getRiskShadow = () => {
    switch (item.severity) {
      case 'red': return 'shadow-[0_0_40px_rgba(255,90,90,.25)]'
      case 'amber': return 'shadow-[0_0_32px_rgba(255,210,70,.18)]'
      default: return 'shadow-[0_0_28px_rgba(61,234,187,.18)]'
    }
  }

  return (
    <motion.button
      ref={isDraggable ? drag : undefined}
      initial={{ opacity: 0, scale: 0.9, y: 20 }}
      animate={{ 
        opacity: isDragging ? 0.7 : 1, 
        scale: isDragging ? 1.02 : 1, 
        y: 0,
        rotate: isDragging ? 1 : 0
      }}
      transition={{ 
        delay: index * 0.1,
        duration: 0.6,
        ease: [0.25, 0.46, 0.45, 0.94]
      }}
      whileHover={{ 
        scale: isDragging ? 1.02 : 1.01,
        y: isDragging ? 0 : -2,
        transition: { duration: 0.3, ease: 'easeOut' }
      }}
      whileTap={{ scale: 0.995 }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => onSelect()}
      className={clsx(
        'group relative w-full h-[190px] rounded-3xl p-5 text-left',
        'backdrop-blur-xl border border-white/10 overflow-hidden',
        getRiskShadow(),
        isDraggable && 'cursor-move',
        isDragging && 'z-50'
      )}
      style={{
        background: `
          linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.02)),
          radial-gradient(120% 140% at 0% 0%, ${gradient.a} 0%, transparent 60%),
          radial-gradient(120% 140% at 100% 100%, ${gradient.b} 0%, transparent 60%),
          ${gradient.base}
        `
      }}
    >
      {/* Glass highlight */}
      <div 
        className="absolute inset-0 rounded-3xl pointer-events-none" 
        style={{
          boxShadow: "inset 0 1px 0 rgba(255,255,255,.25)",
          maskImage: "radial-gradient(140% 100% at 50% 0%, black 40%, transparent 100%)"
        }}
      />

      {/* Clean top area - no indicators */}

      {/* Main content */}
      <div className="h-full flex flex-col">
        {/* Title - starts from top */}
        <h3 className="text-white/90 font-semibold text-lg leading-tight mb-3 line-clamp-2">
          {item.title || "Untitled idea"}
        </h3>

        {/* Summary */}
        <div className="flex-1">
          {item.summary && (
            <p className="text-white/70 text-sm line-clamp-3 leading-relaxed mb-3">
              {item.summary}
            </p>
          )}

          {/* Status - only if meaningful */}
          {(prdProgress > 0 || hasPRD || prdFrozen) && (
            <div className="text-white/60 text-xs">
              {getTriageStatus()}
            </div>
          )}
        </div>

        {/* Bottom section - progress and actions */}
        <div className="flex items-center justify-between mt-4">
          <div className="flex items-center gap-3">
            <ProgressRing value={prdProgress} />
            <span className="text-white/50 text-xs">
              {getTriageStatus()}
            </span>
          </div>
          <div className="flex gap-2">
            <button
              onClick={(e) => {
                e.stopPropagation()
                onAction(item.id, 'promote')
              }}
              className="px-3 py-1.5 rounded-lg bg-white/10 text-white/80 hover:bg-white/16 text-xs font-medium transition-colors"
            >
              Promote
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation()
                onAction(item.id, 'snooze')
              }}
              className="px-3 py-1.5 rounded-lg bg-black/30 border border-white/10 text-white/70 hover:bg-black/40 text-xs font-medium transition-colors"
            >
              Snooze
            </button>
          </div>
        </div>
      </div>

      {/* Soft aura at bottom */}
      <div 
        className="absolute left-6 right-6 bottom-3 h-[2px] rounded-full"
        style={{
          boxShadow: "0 0 30px rgba(255,0,180,.25), 0 0 18px rgba(0,255,200,.15)"
        }}
      />

      {/* Selection indicator */}
      {isSelected && (
        <div className="absolute inset-0 rounded-3xl ring-2 ring-white/30 ring-offset-2 ring-offset-transparent" />
      )}
    </motion.button>
  )
}

export default AppleStyleIdeaCard