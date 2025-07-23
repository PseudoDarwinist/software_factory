/**
 * HealthPill Component - System health status indicator
 * 
 * This component displays the overall system health as a colored pill
 * with real-time updates. Colors indicate health status:
 * - Green: Healthy (score >= 80)
 * - Amber: Warning (score 50-79)
 * - Red: Critical (score < 50)
 * 
 * Why this component exists:
 * - Provides immediate visual feedback on system health
 * - Implements the design requirement for header health indicator
 * - Updates in real-time to reflect current system status
 * 
 * For AI agents: This is the health status pill shown in the settings header.
 */

import React from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { tokens } from '@/styles/tokens'
import type { SystemHealth, HealthStatus } from '@/types/monitoring'

interface HealthPillProps {
  health: SystemHealth
  showLabel?: boolean
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export const HealthPill: React.FC<HealthPillProps> = ({
  health,
  showLabel = false,
  size = 'md',
  className,
}) => {
  const getHealthColor = (status: HealthStatus) => {
    switch (status) {
      case 'healthy':
        return {
          bg: 'bg-green-500/20',
          border: 'border-green-500/50',
          text: 'text-green-400',
          glow: 'shadow-green-500/20',
          dot: 'bg-green-400',
        }
      case 'warning':
        return {
          bg: 'bg-amber-500/20',
          border: 'border-amber-500/50',
          text: 'text-amber-400',
          glow: 'shadow-amber-500/20',
          dot: 'bg-amber-400',
        }
      case 'critical':
        return {
          bg: 'bg-red-500/20',
          border: 'border-red-500/50',
          text: 'text-red-400',
          glow: 'shadow-red-500/20',
          dot: 'bg-red-400',
        }
      default:
        return {
          bg: 'bg-white/5',
          border: 'border-white/20',
          text: 'text-white/60',
          glow: 'shadow-white/10',
          dot: 'bg-white/40',
        }
    }
  }

  const getSizeClasses = (size: 'sm' | 'md' | 'lg') => {
    switch (size) {
      case 'sm':
        return {
          container: 'px-2 py-1 text-xs',
          dot: 'w-2 h-2',
          gap: 'space-x-1.5',
        }
      case 'md':
        return {
          container: 'px-3 py-1.5 text-sm',
          dot: 'w-2.5 h-2.5',
          gap: 'space-x-2',
        }
      case 'lg':
        return {
          container: 'px-4 py-2 text-base',
          dot: 'w-3 h-3',
          gap: 'space-x-2.5',
        }
    }
  }

  const getStatusLabel = (status: HealthStatus, score: number) => {
    switch (status) {
      case 'healthy':
        return 'Healthy'
      case 'warning':
        return 'Warning'
      case 'critical':
        return 'Critical'
      default:
        return 'Unknown'
    }
  }

  const colors = getHealthColor(health.status)
  const sizes = getSizeClasses(size)

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
      className={clsx(
        'inline-flex items-center rounded-full backdrop-blur-sm',
        'border transition-all duration-200',
        colors.bg,
        colors.border,
        colors.text,
        sizes.container,
        sizes.gap,
        'shadow-lg',
        colors.glow,
        className
      )}
    >
      {/* Status Dot with Pulse Animation */}
      <div className="relative">
        <motion.div
          className={clsx(
            'rounded-full',
            colors.dot,
            sizes.dot
          )}
          animate={{
            scale: [1, 1.2, 1],
            opacity: [1, 0.8, 1],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
        
        {/* Pulse Ring */}
        <motion.div
          className={clsx(
            'absolute inset-0 rounded-full border-2',
            colors.dot.replace('bg-', 'border-'),
            'opacity-30'
          )}
          animate={{
            scale: [1, 1.5],
            opacity: [0.3, 0],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: 'easeOut',
          }}
        />
      </div>

      {/* Status Text */}
      {showLabel && (
        <span className="font-medium">
          {getStatusLabel(health.status, health.overallScore)}
        </span>
      )}

      {/* Health Score */}
      <span className="font-mono text-xs opacity-80">
        {Math.round(health.overallScore)}%
      </span>
    </motion.div>
  )
}

export default HealthPill