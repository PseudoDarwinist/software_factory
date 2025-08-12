import React from 'react'
import { GlassBackground } from '@/components/core/GlassBackground'

interface LeftSidebarProps {
  runningCount?: number
  reviewItems?: Array<{ id: string; title: string; severity: 'warning' | 'error' }>
}

export const LeftSidebar: React.FC<LeftSidebarProps> = ({ runningCount = 0, reviewItems = [] }) => {
  return (
    <div className="p-4 space-y-6">
      <GlassBackground className="p-4">
        <h3 className="text-lg font-semibold text-white mb-1">Running</h3>
        <p className="text-sm text-white/60">{runningCount > 0 ? `${runningCount} checks running` : 'No running checks'}</p>
      </GlassBackground>

      <GlassBackground className="p-4">
        <h3 className="text-lg font-semibold text-white mb-3">Review</h3>
        <div className="space-y-2">
          {reviewItems.length === 0 && (
            <p className="text-sm text-white/60">Nothing to review</p>
          )}
          {reviewItems.map(item => (
            <div key={item.id} className="flex items-center space-x-2 text-sm">
              <div className={`w-2 h-2 rounded-full ${item.severity === 'warning' ? 'bg-yellow-500' : 'bg-red-500'}`}></div>
              <span className="text-white/80">{item.title}</span>
            </div>
          ))}
        </div>
      </GlassBackground>
    </div>
  )
}

export default LeftSidebar

