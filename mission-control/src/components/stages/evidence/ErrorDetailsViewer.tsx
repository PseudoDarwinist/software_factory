import React from 'react'
import type { ErrorDetail } from '@/types/validation'
import { GlassBackground } from '@/components/core/GlassBackground'

interface ErrorDetailsViewerProps {
  errors: ErrorDetail[]
}

export const ErrorDetailsViewer: React.FC<ErrorDetailsViewerProps> = ({ errors }) => {
  return (
    <GlassBackground className="p-3">
      <div className="space-y-3 text-sm">
        {errors.map((e, idx) => (
          <div key={idx}>
            <div className="text-red-300 mb-1">{e.message}</div>
            {e.stack && (
              <pre className="whitespace-pre-wrap text-white/70 bg-white/5 rounded p-2 border border-white/10">{e.stack}</pre>
            )}
          </div>
        ))}
        {errors.length === 0 && <div className="text-white/50">No errors.</div>}
      </div>
    </GlassBackground>
  )
}

export default ErrorDetailsViewer

