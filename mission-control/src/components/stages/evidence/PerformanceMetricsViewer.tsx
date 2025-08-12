import React from 'react'
import type { PerformanceMetric } from '@/types/validation'
import { GlassBackground } from '@/components/core/GlassBackground'

interface PerformanceMetricsViewerProps {
  metrics: PerformanceMetric[]
}

export const PerformanceMetricsViewer: React.FC<PerformanceMetricsViewerProps> = ({ metrics }) => {
  return (
    <GlassBackground className="p-3">
      <div className="space-y-2">
        {metrics.map((m, idx) => (
          <div key={idx} className="flex items-center justify-between text-sm">
            <span className="text-white/80">{m.name}</span>
            <span className="text-white/60">{m.value.toFixed(0)}{m.unit}{m.target ? ` (target ${m.target}${m.unit})` : ''}</span>
          </div>
        ))}
        {metrics.length === 0 && <div className="text-white/50">No performance metrics.</div>}
      </div>
    </GlassBackground>
  )
}

export default PerformanceMetricsViewer

