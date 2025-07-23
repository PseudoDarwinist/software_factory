/**
 * MetricCard Component - Individual metric display card
 * 
 * This component displays a single metric with value, trend, and visual styling
 * consistent with the cyber-grid theme. It includes animated transitions and
 * color-coded status indicators.
 * 
 * Why this component exists:
 * - Provides consistent metric display across the dashboard
 * - Implements the grid paper backdrop and glass morphism styling
 * - Shows trend indicators and status colors
 * - Supports real-time value updates with smooth animations
 * 
 * For AI agents: This is a reusable metric card for displaying dashboard statistics.
 */

import React from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import { tokens } from '@/styles/tokens'

interface MetricCardProps {
  title: string
  value: number
  unit?: string
  trend?: 'up' | 'down' | 'stable'
  color: 'green' | 'amber' | 'red' | 'blue' | 'purple'
  icon?: string
  subtitle?: string
  className?: string
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  trend = 'stable',
  color,
  icon,
  subtitle,
  className,
}) => {
  const getColorClasses = (color: string) => {
    switch (color) {
      case 'green':
        return {
          accent: 'text-green-400',
          border: 'border-green-500/30',
          glow: 'shadow-green-500/20',
        }
      case 'amber':
        return {
          accent: 'text-amber-400',
          border: 'border-amber-500/30',
          glow: 'shadow-amber-500/20',
        }
      case 'red':
        return {
          accent: 'text-red-400',
          border: 'border-red-500/30',
          glow: 'shadow-red-500/20',
        }
      case 'blue':
        return {
          accent: 'text-blue-400',
          border: 'border-blue-500/30',
          glow: 'shadow-blue-500/20',
        }
      case 'purple':
        return {
          accent: 'text-purple-400',
          border: 'border-purple-500/30',
          glow: 'shadow-purple-500/20',
        }
      default:
        return {
          accent: 'text-white/60',
          border: 'border-white/20',
          glow: 'shadow-white/10',
        }
    }
  }

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up':
        return '↗'
      case 'down':
        return '↘'
      case 'stable':
      default:
        return '→'
    }
  }

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'up':
        return 'text-green-400'
      case 'down':
        return 'text-red-400'
      case 'stable':
      default:
        return 'text-white/60'
    }
  }

  const formatValue = (value: number) => {
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(1)}M`
    } else if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}K`
    } else if (value % 1 === 0) {
      return value.toString()
    } else {
      return value.toFixed(1)
    }
  }

  const colors = getColorClasses(color)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={clsx(
        'bg-grid rounded-xl p-5 border backdrop-blur-sm',
        'transition-all duration-200 hover:scale-[1.02]',
        colors.border,
        colors.glow,
        'shadow-lg',
        className
      )}
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <h3 className="text-sm uppercase tracking-wide text-white/60 font-medium">
            {title}
          </h3>
          {subtitle && (
            <p className="text-xs text-white/40 mt-1">{subtitle}</p>
          )}
        </div>
        
        {icon && (
          <div className="text-xl opacity-60">
            {icon}
          </div>
        )}
      </div>

      {/* Value */}
      <div className="mb-3">
        <motion.div
          key={value}
          initial={{ scale: 1.1, opacity: 0.8 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.2 }}
          className="flex items-baseline space-x-1"
        >
          <span className={clsx('text-3xl font-semibold', colors.accent)}>
            {formatValue(value)}
          </span>
          {unit && (
            <span className="text-sm text-white/60 font-medium">
              {unit}
            </span>
          )}
        </motion.div>
      </div>

      {/* Trend Indicator */}
      <div className="flex items-center space-x-2">
        <span className={clsx('text-sm font-medium', getTrendColor(trend))}>
          {getTrendIcon(trend)}
        </span>
        <span className="text-xs text-white/60">
          {trend === 'up' ? 'Increasing' : 
           trend === 'down' ? 'Decreasing' : 
           'Stable'}
        </span>
      </div>
    </motion.div>
  )
}

export default MetricCard