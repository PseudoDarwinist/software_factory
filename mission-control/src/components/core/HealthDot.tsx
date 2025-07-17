/**
 * HealthDot - Breathing health indicator component
 * 
 * This component creates the revolutionary "breathing" health indicators that:
 * - Pulse at different speeds based on project health
 * - Glow with appropriate colors
 * - Provide intuitive visual feedback
 * 
 * Why this component exists:
 * - Replaces static dots with living, breathing indicators
 * - Provides immediate visual feedback about project health
 * - Creates an organic, alive feeling in the interface
 * 
 * For AI agents: Use this component whenever you need to show project health status.
 * The `health` prop controls both color and animation speed.
 */

import React, { useEffect, useRef } from 'react'
import { motion, useAnimation } from 'framer-motion'
import { useSpring, animated } from '@react-spring/web'
import { clsx } from 'clsx'
import { tokens } from '@/styles/tokens'
import type { ProjectHealth } from '@/types'

interface HealthDotProps {
  health: ProjectHealth
  size?: 'sm' | 'md' | 'lg'
  showGlow?: boolean
  showPulse?: boolean
  interactive?: boolean
  className?: string
  onClick?: () => void
  'aria-label'?: string
}

export const HealthDot: React.FC<HealthDotProps> = ({
  health,
  size = 'md',
  showGlow = true,
  showPulse = true,
  interactive = false,
  className,
  onClick,
  'aria-label': ariaLabel,
}) => {
  const controls = useAnimation()
  const dotRef = useRef<HTMLDivElement>(null)

  // Size configurations
  const sizeConfig = {
    sm: { width: '8px', height: '8px', glowSize: '16px' },
    md: { width: '12px', height: '12px', glowSize: '24px' },
    lg: { width: '16px', height: '16px', glowSize: '32px' },
  }

  // Health-based configurations
  const healthConfig = {
    green: {
      color: tokens.colors.status.green.solid,
      glowColor: tokens.colors.status.green.glow,
      pulseColor: tokens.colors.status.green.pulse,
      pulseDuration: 4000, // Slow, peaceful pulse
      pulseScale: 1.2,
      description: 'healthy',
    },
    amber: {
      color: tokens.colors.status.amber.solid,
      glowColor: tokens.colors.status.amber.glow,
      pulseColor: tokens.colors.status.amber.pulse,
      pulseDuration: 2000, // Medium pulse - mild concern
      pulseScale: 1.4,
      description: 'needs attention',
    },
    red: {
      color: tokens.colors.status.red.solid,
      glowColor: tokens.colors.status.red.glow,
      pulseColor: tokens.colors.status.red.pulse,
      pulseDuration: 1000, // Fast pulse - urgent
      pulseScale: 1.6,
      description: 'critical',
    },
  }

  const config = healthConfig[health]
  const sizes = sizeConfig[size]

  // Breathing animation spring
  const breathingSpring = useSpring({
    transform: showPulse ? `scale(1)` : 'scale(1)',
    config: { tension: 300, friction: 10 },
  })

  // Glow effect spring
  const glowSpring = useSpring({
    opacity: showGlow ? 0.6 : 0,
    transform: showGlow ? `scale(1)` : 'scale(0.8)',
    config: { tension: 200, friction: 20 },
  })

  // Pulse animation effect
  useEffect(() => {
    if (!showPulse) return

    const animate = async () => {
      await controls.start({
        scale: [1, config.pulseScale, 1],
        opacity: [1, 0.7, 1],
        transition: {
          duration: config.pulseDuration / 1000,
          repeat: Infinity,
          ease: 'easeInOut',
        },
      })
    }

    animate()
  }, [health, showPulse, controls, config])

  // Interactive states
  const [isHovered, setIsHovered] = React.useState(false)
  const [isPressed, setIsPressed] = React.useState(false)

  const handleMouseEnter = () => {
    if (!interactive) return
    setIsHovered(true)
  }

  const handleMouseLeave = () => {
    if (!interactive) return
    setIsHovered(false)
  }

  const handleClick = () => {
    if (!interactive) return
    setIsPressed(true)
    onClick?.()
    setTimeout(() => setIsPressed(false), 150)
  }

  return (
    <div
      className={clsx(
        'relative flex items-center justify-center',
        interactive && 'cursor-pointer',
        className
      )}
      style={{ width: sizes.glowSize, height: sizes.glowSize }}
      onClick={handleClick}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      aria-label={ariaLabel || `Project health: ${config.description}`}
      role={interactive ? 'button' : 'status'}
      tabIndex={interactive ? 0 : -1}
    >
      {/* Outer glow effect */}
      {showGlow && (
        <animated.div
          className="absolute inset-0 rounded-full"
          style={{
            background: `radial-gradient(circle, ${config.glowColor} 0%, transparent 70%)`,
            ...glowSpring,
          }}
        />
      )}

      {/* Pulse ring */}
      {showPulse && (
        <motion.div
          animate={controls}
          className="absolute rounded-full border-2 opacity-30"
          style={{
            width: sizes.width,
            height: sizes.height,
            borderColor: config.color,
            left: '50%',
            top: '50%',
            transform: 'translate(-50%, -50%)',
          }}
        />
      )}

      {/* Main dot */}
      <animated.div
        ref={dotRef}
        className={clsx(
          'rounded-full relative z-10',
          'transition-all duration-200',
          isHovered && 'scale-110',
          isPressed && 'scale-95'
        )}
        style={{
          width: sizes.width,
          height: sizes.height,
          backgroundColor: config.color,
          boxShadow: `0 0 8px ${config.glowColor}`,
          ...breathingSpring,
        }}
      />

      {/* Click ripple effect */}
      {isPressed && (
        <motion.div
          className="absolute rounded-full border-2 opacity-50"
          style={{
            borderColor: config.color,
            left: '50%',
            top: '50%',
            transform: 'translate(-50%, -50%)',
          }}
          initial={{ width: sizes.width, height: sizes.height }}
          animate={{ 
            width: sizes.glowSize, 
            height: sizes.glowSize,
            opacity: 0 
          }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        />
      )}
    </div>
  )
}

export default HealthDot