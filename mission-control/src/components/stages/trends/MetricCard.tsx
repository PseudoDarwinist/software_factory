import React from 'react'
import { GlassBackground } from '@/components/core/GlassBackground'

interface MetricCardProps {
  label: string
  value: string | number
  sublabel?: string
  intent?: 'neutral' | 'good' | 'warn' | 'bad'
}

export const MetricCard: React.FC<MetricCardProps> = ({ label, value, sublabel, intent = 'neutral' }) => {
  const color = intent === 'good' ? 'text-green-400' : intent === 'warn' ? 'text-amber-300' : intent === 'bad' ? 'text-red-400' : 'text-white'
  return (
    <GlassBackground className="p-4">
      <div className="text-xs text-white/60 mb-1">{label}</div>
      <div className={`text-2xl font-semibold ${color}`}>{value}</div>
      {sublabel && <div className="text-xs text-white/40 mt-1">{sublabel}</div>}
    </GlassBackground>
  )
}

export default MetricCard

