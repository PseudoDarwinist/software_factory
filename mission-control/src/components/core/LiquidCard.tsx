/**
 * LiquidCard - Core card component with liquid glass morphism
 * 
 * This component implements the "Jony Ive on Acid" aesthetic with:
 * - Liquid glass morphism effects
 * - Breathing animations based on content urgency
 * - Magnetic field interactions
 * - Organic shape transformations
 * 
 * Why this component exists:
 * - Provides consistent liquid glass aesthetic across all cards
 * - Centralizes complex visual effects and animations
 * - Enables dynamic behavior based on content type and urgency
 * 
 * For AI agents: Use this as the base for all card-like components.
 * The `variant` prop controls the visual style, `urgency` controls animations.
 */

import React, { useState, useEffect, useRef } from 'react'
import { motion, useAnimation } from 'framer-motion'
import { useSpring, animated } from 'react-spring'
import { clsx } from 'clsx'
import { tokens } from '@/styles/tokens'
import type { FeedSeverity } from '@/types'

interface LiquidCardProps {
  children: React.ReactNode
  variant?: 'default' | 'feed' | 'project' | 'conversation'
  severity?: FeedSeverity
  urgency?: 'low' | 'medium' | 'high'
  interactive?: boolean
  className?: string
  onClick?: () => void
  onHover?: (isHovered: boolean) => void
  style?: React.CSSProperties
  breathingAnimation?: boolean
  glowEffect?: boolean
  magneticEffect?: boolean
  id?: string
}

export const LiquidCard: React.FC<LiquidCardProps> = ({
  children,
  variant = 'default',
  severity = 'info',
  urgency = 'low',
  interactive = true,
  className,
  onClick,
  onHover,
  style,
  breathingAnimation = true,
  magneticEffect = true,
  id,
}) => {
  // State for hover and interactions
  const [isHovered, setIsHovered] = useState(false)
  const [isPressed, setIsPressed] = useState(false)
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })
  const cardRef = useRef<HTMLDivElement>(null)
  const controls = useAnimation()

  // Breathing animation based on urgency
  const breathingConfig = {
    low: { scale: [1, 1.02, 1], duration: 4000 },
    medium: { scale: [1, 1.05, 1], duration: 2000 },
    high: { scale: [1, 1.08, 1], duration: 1000 },
  }

  // Glow intensity based on severity
  const glowIntensity = {
    info: 0.1,
    amber: 0.3,
    red: 0.5,
  }

  // Spring animation for liquid morphing
  const liquidSpring = useSpring({
    transform: isHovered 
      ? `perspective(1000px) rotateX(${(mousePosition.y - 0.5) * 10}deg) rotateY(${(mousePosition.x - 0.5) * 10}deg) scale(1.02)`
      : 'perspective(1000px) rotateX(0deg) rotateY(0deg) scale(1)',
    backdropFilter: isHovered 
      ? `blur(16px) saturate(1.4) brightness(1.1)`
      : `blur(12px) saturate(1.2) brightness(1.05)`,
    background: isHovered
      ? `rgba(150, 179, 150, ${0.15 + glowIntensity[severity] * 0.1})`
      : `rgba(150, 179, 150, 0.08)`,
    boxShadow: isHovered
      ? `0 20px 40px rgba(0, 0, 0, 0.15), 0 0 30px rgba(150, 179, 150, ${glowIntensity[severity]})`
      : `0 8px 32px rgba(0, 0, 0, 0.1), 0 0 20px rgba(150, 179, 150, ${glowIntensity[severity] * 0.5})`,
    config: { tension: 280, friction: 60 },
  })

  // Magnetic field effect
  const handleMouseMove = (e: React.MouseEvent) => {
    if (!magneticEffect || !cardRef.current) return
    
    const rect = cardRef.current.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width
    const y = (e.clientY - rect.top) / rect.height
    
    setMousePosition({ x, y })
  }

  // Breathing animation effect
  useEffect(() => {
    if (!breathingAnimation) return

    const animate = async () => {
      const config = breathingConfig[urgency]
      await controls.start({
        scale: config.scale,
        transition: {
          duration: config.duration / 1000,
          repeat: Infinity,
          ease: 'easeInOut',
        },
      })
    }

    animate()
  }, [urgency, breathingAnimation, controls])

  // Handle hover state
  const handleMouseEnter = () => {
    setIsHovered(true)
    onHover?.(true)
  }

  const handleMouseLeave = () => {
    setIsHovered(false)
    setMousePosition({ x: 0, y: 0 })
    onHover?.(false)
  }

  // Click handler with press animation
  const handleClick = () => {
    if (!interactive) return
    
    setIsPressed(true)
    onClick?.()
    
    // Reset press state after animation
    setTimeout(() => setIsPressed(false), 150)
  }

  // Dynamic styles based on variant
  const getVariantStyles = () => {
    switch (variant) {
      case 'feed':
        return {
          minHeight: '80px',
          padding: tokens.spacing[4],
          borderRadius: tokens.borderRadius.lg,
        }
      case 'project':
        return {
          minHeight: '60px',
          padding: tokens.spacing[3],
          borderRadius: tokens.borderRadius.md,
        }
      case 'conversation':
        return {
          minHeight: '120px',
          padding: tokens.spacing[6],
          borderRadius: tokens.borderRadius.xl,
        }
      default:
        return {
          padding: tokens.spacing[4],
          borderRadius: tokens.borderRadius.glass,
        }
    }
  }

  return (
    <motion.div
      ref={cardRef}
      animate={controls}
      initial={{ scale: 1 }}
      whileTap={interactive ? { scale: 0.98 } : {}}
      className={clsx(
        'relative overflow-hidden',
        'border border-white/8',
        'transition-all duration-300',
        interactive && 'cursor-pointer',
        className
      )}
      style={{
        ...getVariantStyles(),
        ...style,
      }}
      onMouseMove={handleMouseMove}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={handleClick}
      id={id}
    >
      {/* Liquid glass background */}
      <animated.div
        className="absolute inset-0 -z-10"
        style={liquidSpring}
      />
      
      {/* Gradient overlay for depth */}
      <div className="absolute inset-0 -z-10 bg-gradient-to-br from-white/5 via-transparent to-black/20" />
      
      {/* Shimmer effect on hover */}
      {isHovered && (
        <motion.div
          className="absolute inset-0 -z-10"
          initial={{ opacity: 0, x: '-100%' }}
          animate={{ opacity: 1, x: '100%' }}
          transition={{ duration: 0.8, ease: 'easeInOut' }}
          style={{
            background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent)',
          }}
        />
      )}
      
      {/* Status indicator for feed items */}
      {variant === 'feed' && (
        <div 
          className={clsx(
            'absolute top-2 right-2 w-2 h-2 rounded-full',
            severity === 'info' && 'bg-blue-500',
            severity === 'amber' && 'bg-amber-500',
            severity === 'red' && 'bg-red-500',
          )}
          style={{
            boxShadow: `0 0 8px ${tokens.colors.status[severity]?.glow}`,
          }}
        />
      )}
      
      {/* Content */}
      <div className="relative z-10 h-full flex flex-col">
        {children}
      </div>
      
      {/* Ripple effect on click */}
      {isPressed && (
        <motion.div
          className="absolute inset-0 bg-white/10 rounded-full -z-10"
          initial={{ scale: 0, opacity: 0.5 }}
          animate={{ scale: 4, opacity: 0 }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        />
      )}
    </motion.div>
  )
}

export default LiquidCard