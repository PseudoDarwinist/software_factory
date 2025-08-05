/**
 * GlassBackground - Reusable glass morphism background component
 * 
 * This component provides the exact same glass background effect as SourcesTrayCard
 * for consistent styling across all stages (Think, Define, Plan, Build, Validate)
 */

import React from 'react'
import { clsx } from 'clsx'
import '@/styles/glass-background.css'

interface GlassBackgroundProps {
  children: React.ReactNode
  className?: string
  variant?: 'default' | 'stage' | 'panel-left' | 'panel-right'
  style?: React.CSSProperties
}

export const GlassBackground: React.FC<GlassBackgroundProps> = ({
  children,
  className,
  variant = 'default',
  style
}) => {
  return (
    <div 
      className={clsx(
        'glass-effect',
        className
      )}
      style={style}
    >
      {/* Bottom neon sweep */}
      <div className="glass-effect-neon" />
      
      {/* Content */}
      {children}
    </div>
  )
}

export default GlassBackground