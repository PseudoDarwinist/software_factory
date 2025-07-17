/**
 * StageBar - Navigation bar for SDLC stages
 * 
 * This component provides navigation between the five rooms of Software Factory:
 * Think → Define → Plan → Build → Validate
 * 
 * Features:
 * - Liquid glass morphing tabs
 * - Animated stage transitions
 * - Drag-and-drop target for moving items between stages
 * - Mobile-responsive design
 * 
 * Why this component exists:
 * - Provides clear navigation between SDLC stages
 * - Enables drag-and-drop workflow for moving items
 * - Maintains visual consistency with liquid glass theme
 * 
 * For AI agents: This is the main navigation for Software Factory stages.
 * The `activeStage` prop controls which tab is highlighted.
 */

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useDrop } from 'react-dnd'
import { clsx } from 'clsx'
import { tokens } from '@/styles/tokens'
import type { SDLCStage } from '@/types'

interface StageBarProps {
  activeStage: SDLCStage
  onStageChange: (stage: SDLCStage) => void
  showBackButton?: boolean
  onBackClick?: () => void
  className?: string
  onItemDrop?: (itemId: string, fromStage: SDLCStage, toStage: SDLCStage) => void
  selectedProject?: string | null
}

const stages: { id: SDLCStage; label: string; icon: string; description: string }[] = [
  {
    id: 'think',
    label: 'Think',
    icon: '💭',
    description: 'Capture ideas and thoughts',
  },
  {
    id: 'define',
    label: 'Define',
    icon: '📝',
    description: 'Create product briefs and specs',
  },
  {
    id: 'plan',
    label: 'Plan',
    icon: '📋',
    description: 'Break down work into tasks',
  },
  {
    id: 'build',
    label: 'Build',
    icon: '🔨',
    description: 'Write code and implement features',
  },
  {
    id: 'validate',
    label: 'Validate',
    icon: '✅',
    description: 'Test and validate implementation',
  },
]

export const StageBar: React.FC<StageBarProps> = ({
  activeStage,
  onStageChange,
  showBackButton = false,
  onBackClick,
  className,
  onItemDrop,
  selectedProject,
}) => {
  const [hoveredStage, setHoveredStage] = useState<SDLCStage | null>(null)
  const [dragOverStage, setDragOverStage] = useState<SDLCStage | null>(null)

  return (
    <div className={clsx(
      'fixed top-0 left-0 right-0 z-50',
      'bg-black/40 backdrop-blur-md',
      'border-b border-white/10',
      'px-4 py-3',
      className
    )}>
      <div className="flex items-center justify-between max-w-7xl mx-auto">
        {/* Back button for mobile */}
        <AnimatePresence>
          {showBackButton && (
            <motion.button
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              onClick={onBackClick}
              className="flex items-center space-x-2 text-white/80 hover:text-white transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              <span className="text-sm">Back</span>
            </motion.button>
          )}
        </AnimatePresence>

        {/* Stage Navigation */}
        <div className="flex items-center space-x-1">
          {stages.map((stage, index) => {
            const isActive = activeStage === stage.id
            const isHovered = hoveredStage === stage.id
            const isDragOver = dragOverStage === stage.id
            const isAccessible = index === 0 || stages[index - 1].id === activeStage || isActive

            return (
              <StageTab
                key={stage.id}
                stage={stage}
                isActive={isActive}
                isHovered={isHovered}
                isDragOver={isDragOver}
                isAccessible={isAccessible}
                onHover={setHoveredStage}
                onDragOver={setDragOverStage}
                onClick={() => onStageChange(stage.id)}
                onItemDrop={onItemDrop}
                selectedProject={selectedProject}
                currentStage={activeStage}
              />
            )
          })}
        </div>

        {/* Mission Control indicator */}
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
          <span className="text-sm text-white/80 font-medium">Mission Control</span>
        </div>
      </div>
    </div>
  )
}

interface StageTabProps {
  stage: { id: SDLCStage; label: string; icon: string; description: string }
  isActive: boolean
  isHovered: boolean
  isDragOver: boolean
  isAccessible: boolean
  onHover: (stage: SDLCStage | null) => void
  onDragOver: (stage: SDLCStage | null) => void
  onClick: () => void
  onItemDrop?: (itemId: string, fromStage: SDLCStage, toStage: SDLCStage) => void
  selectedProject?: string | null
  currentStage: SDLCStage
}

const StageTab: React.FC<StageTabProps> = ({
  stage,
  isActive,
  isHovered,
  isDragOver,
  isAccessible,
  onHover,
  onDragOver,
  onClick,
  onItemDrop,
  selectedProject,
  currentStage,
}) => {
  // Drag and drop functionality
  const [{ canDrop, isOver }, drop] = useDrop(() => ({
    accept: 'FEED_ITEM',
    drop: (item: { id: string; type: string }) => {
      if (onItemDrop && selectedProject) {
        onItemDrop(item.id, currentStage, stage.id)
      }
      return { stageId: stage.id }
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
      canDrop: monitor.canDrop(),
    }),
  }), [onItemDrop, selectedProject, currentStage, stage.id])

  React.useEffect(() => {
    if (isOver && canDrop) {
      onDragOver(stage.id)
    } else if (isDragOver) {
      onDragOver(null)
    }
  }, [isOver, canDrop, stage.id, isDragOver, onDragOver])

  return (
    <motion.div
      ref={drop}
      className={clsx(
        'relative px-4 py-2 rounded-lg cursor-pointer',
        'transition-all duration-300',
        'select-none',
        !isAccessible && 'opacity-50 cursor-not-allowed',
        isActive && 'text-white',
        !isActive && 'text-white/70 hover:text-white/90',
      )}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      onMouseEnter={() => onHover(stage.id)}
      onMouseLeave={() => onHover(null)}
      onClick={isAccessible ? onClick : undefined}
    >
      {/* Background with liquid glass effect */}
      <motion.div
        className="absolute inset-0 rounded-lg"
        style={{
          background: isActive
            ? 'rgba(150, 179, 150, 0.2)'
            : isHovered || isDragOver
            ? 'rgba(150, 179, 150, 0.1)'
            : 'transparent',
          backdropFilter: isActive ? 'blur(12px)' : 'blur(8px)',
          border: isActive
            ? '1px solid rgba(150, 179, 150, 0.3)'
            : isDragOver
            ? '1px solid rgba(150, 179, 150, 0.5)'
            : '1px solid transparent',
        }}
        animate={{
          scale: isDragOver ? 1.1 : 1,
          opacity: isActive ? 1 : isHovered || isDragOver ? 0.8 : 0.6,
        }}
        transition={{ duration: 0.2 }}
      />

      {/* Glow effect for active stage */}
      {isActive && (
        <motion.div
          className="absolute inset-0 rounded-lg"
          style={{
            background: 'rgba(150, 179, 150, 0.1)',
            filter: 'blur(8px)',
            transform: 'scale(1.2)',
          }}
          animate={{ opacity: [0.3, 0.6, 0.3] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
      )}

      {/* Content */}
      <div className="relative z-10 flex items-center space-x-2">
        <span className="text-lg" role="img" aria-label={stage.description}>
          {stage.icon}
        </span>
        <span className="font-medium text-sm">{stage.label}</span>
      </div>

      {/* Drag over indicator */}
      {isDragOver && (
        <motion.div
          className="absolute -top-1 -bottom-1 -left-1 -right-1 rounded-lg"
          style={{
            border: '2px dashed rgba(150, 179, 150, 0.6)',
            background: 'rgba(150, 179, 150, 0.05)',
          }}
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 0.8, repeat: Infinity }}
        />
      )}

      {/* Tooltip */}
      <AnimatePresence>
        {isHovered && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="absolute top-full left-1/2 transform -translate-x-1/2 mt-2 z-50"
          >
            <div className="bg-black/80 backdrop-blur-sm rounded-lg px-3 py-2 text-xs text-white/90 whitespace-nowrap">
              {stage.description}
              <div className="absolute -top-1 left-1/2 transform -translate-x-1/2 w-2 h-2 bg-black/80 rotate-45" />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default StageBar