import React from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'
import type { ValidationCheck } from '@/types/validation'

interface ValidationCheckItemProps {
  check: ValidationCheck
  selected?: boolean
  onClick: (id: string) => void
}

const statusIcon: Record<ValidationCheck['status'], string> = {
  success: '✓',
  warning: '⚠',
  error: '✗',
  running: '⟳',
  pending: '○',
}

const statusColor: Record<ValidationCheck['status'], string> = {
  success: 'text-green-400',
  warning: 'text-yellow-400',
  error: 'text-red-400',
  running: 'text-blue-400',
  pending: 'text-gray-400',
}

const formatTime = (date: Date) => date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' })

const formatDuration = (ms?: number) => {
  if (!ms) return ''
  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  if (minutes > 0) return `${minutes}m ${seconds % 60}s`
  return `${seconds}s`
}

export const ValidationCheckItem: React.FC<ValidationCheckItemProps> = ({ check, selected = false, onClick }) => {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ type: 'spring', stiffness: 300, damping: 28 }}
      className={clsx(
        'flex items-center justify-between p-3 cursor-pointer transition-all duration-200',
        'hover:bg-white/5 border-l-2',
        selected ? 'bg-white/10 border-l-blue-400' : 'border-l-transparent'
      )}
      onClick={() => onClick(check.id)}
    >
      <div className="flex items-center space-x-3">
        <span className="text-xs text-white/40 font-mono w-20">
          {formatTime(check.timestamp)}{check.duration ? ` • ${formatDuration(check.duration)}` : ''}
        </span>
        <span className="text-white/80">{check.name}</span>
        <span className="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded bg-white/5 border border-white/10 text-white/60">{check.type}</span>
        {check.priority && (
          <span className={clsx(
            'text-[10px] uppercase tracking-wide px-2 py-0.5 rounded border',
            check.priority === 'high' && 'text-red-300 bg-red-500/10 border-red-500/30',
            check.priority === 'medium' && 'text-amber-300 bg-amber-500/10 border-amber-500/30',
            check.priority === 'low' && 'text-blue-300 bg-blue-500/10 border-blue-500/30'
          )}>{check.priority}</span>
        )}
        {check.status === 'success' && check.metadata?.passRate && (
          <span className="text-xs text-green-400">{check.metadata.passRate}</span>
        )}
      </div>
      <div className="flex items-center space-x-2">
        {check.status === 'warning' && (
          <span className="text-xs text-yellow-400 bg-yellow-400/10 px-2 py-1 rounded">late</span>
        )}
        <span className={clsx('text-lg', statusColor[check.status])}>{statusIcon[check.status]}</span>
      </div>
    </motion.div>
  )
}

export default ValidationCheckItem

