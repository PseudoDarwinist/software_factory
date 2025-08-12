import React from 'react'
import type { TestResult } from '@/types/validation'
import { GlassBackground } from '@/components/core/GlassBackground'

interface TestResultsViewerProps {
  results: TestResult[]
}

export const TestResultsViewer: React.FC<TestResultsViewerProps> = ({ results }) => {
  const passes = results.filter(r => r.status === 'pass').length
  const fails = results.filter(r => r.status === 'fail').length
  const skips = results.filter(r => r.status === 'skip').length

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 text-sm">
        <span className="text-green-400">pass {passes}</span>
        <span className="text-red-400">fail {fails}</span>
        <span className="text-white/60">skip {skips}</span>
      </div>
      <GlassBackground className="p-3">
        <div className="space-y-2 text-sm">
          {results.map((t, idx) => (
            <div key={idx} className="flex items-center justify-between">
              <span className="text-white/80">{t.name}</span>
              <span className={`${t.status === 'pass' ? 'text-green-400' : t.status === 'fail' ? 'text-red-400' : 'text-white/50'}`}>
                {t.status}{t.durationMs ? ` • ${Math.round(t.durationMs)}ms` : ''}
              </span>
            </div>
          ))}
          {results.length === 0 && <div className="text-white/50">No test results.</div>}
        </div>
      </GlassBackground>
    </div>
  )
}

export default TestResultsViewer

