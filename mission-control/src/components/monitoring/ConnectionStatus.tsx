/**
 * ConnectionStatus Component - WebSocket connection status indicator
 * 
 * This component displays the current WebSocket connection status with
 * visual indicators and connection controls. It provides real-time feedback
 * about the monitoring system's connectivity.
 * 
 * Features:
 * - Visual connection status indicators (green/amber/red)
 * - Connection controls (connect/disconnect)
 * - Reconnection status and progress
 * - Error message display
 * - Animated status indicators
 * 
 * Why this component exists:
 * - Provides immediate feedback on connection status
 * - Allows manual connection control
 * - Shows reconnection progress and errors
 * - Implements the design requirement for connection status indicators
 * 
 * For AI agents: This component shows WebSocket connection status for monitoring.
 */

import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { useMonitoringWebSocket } from '@/hooks/useMonitoringWebSocket'

interface ConnectionStatusProps {
  className?: string
  showControls?: boolean
  showDetails?: boolean
  compact?: boolean
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  className,
  showControls = false,
  showDetails = false,
  compact = false,
}) => {
  const {
    connectionStatus,
    connect,
    disconnect,
    isConnected,
    isConnecting,
    hasError,
    error,
    reconnectAttempts,
  } = useMonitoringWebSocket({ autoConnect: true })

  const getStatusColor = () => {
    if (isConnected) return 'green'
    if (isConnecting || reconnectAttempts > 0) return 'amber'
    if (hasError) return 'red'
    return 'gray'
  }

  const getStatusText = () => {
    if (isConnected) return 'Connected'
    if (isConnecting) return 'Connecting...'
    if (reconnectAttempts > 0) return `Reconnecting... (${reconnectAttempts})`
    if (hasError) return 'Disconnected'
    return 'Offline'
  }

  const getStatusIcon = () => {
    if (isConnected) return '🟢'
    if (isConnecting || reconnectAttempts > 0) return '🟡'
    if (hasError) return '🔴'
    return '⚫'
  }

  const colorClasses = {
    green: {
      dot: 'bg-green-400',
      text: 'text-green-400',
      border: 'border-green-500/30',
      glow: 'shadow-green-500/20',
    },
    amber: {
      dot: 'bg-amber-400',
      text: 'text-amber-400',
      border: 'border-amber-500/30',
      glow: 'shadow-amber-500/20',
    },
    red: {
      dot: 'bg-red-400',
      text: 'text-red-400',
      border: 'border-red-500/30',
      glow: 'shadow-red-500/20',
    },
    gray: {
      dot: 'bg-white/40',
      text: 'text-white/60',
      border: 'border-white/20',
      glow: 'shadow-white/10',
    },
  }

  const colors = colorClasses[getStatusColor()]

  if (compact) {
    return (
      <div className={clsx('flex items-center space-x-2', className)}>
        <div className="relative">
          <motion.div
            className={clsx('w-2 h-2 rounded-full', colors.dot)}
            animate={isConnected ? {
              scale: [1, 1.2, 1],
              opacity: [1, 0.8, 1],
            } : isConnecting ? {
              scale: [1, 1.1, 1],
            } : {}}
            transition={isConnected ? {
              duration: 2,
              repeat: Infinity,
            } : isConnecting ? {
              duration: 1,
              repeat: Infinity,
            } : {}}
          />
          
          {/* Pulse ring for connected state */}
          {isConnected && (
            <motion.div
              className={clsx('absolute inset-0 rounded-full border-2', colors.dot.replace('bg-', 'border-'), 'opacity-30')}
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
          )}
        </div>
        
        <span className={clsx('text-xs font-medium', colors.text)}>
          {getStatusText()}
        </span>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className={clsx(
        'bg-white/5 backdrop-blur-sm rounded-lg p-3 border',
        colors.border,
        colors.glow,
        'shadow-lg',
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center space-x-2">
          <span className="text-lg">{getStatusIcon()}</span>
          <div>
            <h4 className="text-sm font-medium text-white">WebSocket</h4>
            <p className={clsx('text-xs', colors.text)}>
              {getStatusText()}
            </p>
          </div>
        </div>
        
        {/* Connection indicator */}
        <div className="relative">
          <motion.div
            className={clsx('w-3 h-3 rounded-full', colors.dot)}
            animate={isConnected ? {
              scale: [1, 1.2, 1],
              opacity: [1, 0.8, 1],
            } : isConnecting ? {
              opacity: [0.5, 1, 0.5],
            } : {}}
            transition={isConnected ? {
              duration: 2,
              repeat: Infinity,
              ease: 'easeInOut',
            } : isConnecting ? {
              duration: 1,
              repeat: Infinity,
            } : {}}
          />
          
          {/* Pulse ring */}
          {(isConnected || isConnecting) && (
            <motion.div
              className={clsx(
                'absolute inset-0 rounded-full border-2 opacity-30',
                colors.dot.replace('bg-', 'border-')
              )}
              animate={{
                scale: [1, 1.8],
                opacity: [0.3, 0],
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                ease: 'easeOut',
              }}
            />
          )}
        </div>
      </div>

      {/* Details */}
      {showDetails && (
        <div className="space-y-2 text-xs text-white/60">
          {connectionStatus.lastConnected && (
            <div>
              <span className="text-white/40">Last connected:</span>
              <span className="ml-2">
                {connectionStatus.lastConnected.toLocaleTimeString()}
              </span>
            </div>
          )}
          
          {reconnectAttempts > 0 && (
            <div>
              <span className="text-white/40">Reconnect attempts:</span>
              <span className="ml-2">{reconnectAttempts}</span>
            </div>
          )}
        </div>
      )}

      {/* Error message */}
      <AnimatePresence>
        {hasError && error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-3 pt-2 border-t border-white/10"
          >
            <div className="flex items-start space-x-2">
              <span className="text-red-400 text-xs mt-0.5">⚠️</span>
              <p className="text-xs text-red-300 flex-1">
                {error}
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Controls */}
      {showControls && (
        <div className="flex items-center space-x-2 mt-3 pt-2 border-t border-white/10">
          {!isConnected && !isConnecting && (
            <motion.button
              onClick={() => connect()}
              className={clsx(
                'px-3 py-1.5 rounded-lg text-xs font-medium',
                'bg-green-500/20 text-green-400 border border-green-500/30',
                'hover:bg-green-500/30 transition-colors'
              )}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Connect
            </motion.button>
          )}
          
          {(isConnected || isConnecting) && (
            <motion.button
              onClick={disconnect}
              className={clsx(
                'px-3 py-1.5 rounded-lg text-xs font-medium',
                'bg-red-500/20 text-red-400 border border-red-500/30',
                'hover:bg-red-500/30 transition-colors'
              )}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Disconnect
            </motion.button>
          )}
        </div>
      )}
    </motion.div>
  )
}

export default ConnectionStatus