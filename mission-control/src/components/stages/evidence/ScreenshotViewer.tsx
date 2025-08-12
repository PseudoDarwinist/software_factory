import React from 'react'
import type { Screenshot } from '@/types/validation'
import { GlassBackground } from '@/components/core/GlassBackground'

interface ScreenshotViewerProps {
  screenshots: Screenshot[]
}

export const ScreenshotViewer: React.FC<ScreenshotViewerProps> = ({ screenshots }) => {
  return (
    <GlassBackground className="p-3">
      <div className="grid grid-cols-2 gap-3">
        {screenshots.map(s => (
          <div key={s.id} className="aspect-video bg-white/5 border border-white/10 rounded flex items-center justify-center text-white/40">
            {s.caption || 'Screenshot'}
          </div>
        ))}
        {screenshots.length === 0 && <div className="text-white/50">No screenshots.</div>}
      </div>
    </GlassBackground>
  )
}

export default ScreenshotViewer

