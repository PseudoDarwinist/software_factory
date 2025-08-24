import React from 'react'
import { clsx } from 'clsx'

interface ValidateLayoutProps {
  sidebar: React.ReactNode
  livePanel: React.ReactNode
  evidencePanel: React.ReactNode
  trendsPanel: React.ReactNode
}

/**
 * ValidateLayout - responsive grid layout for Validate stage
 * - Left sidebar (fixed width)
 * - Center live verification (flex-1)
 * - Right evidence panel (fixed width)
 * - Bottom trends panel (fixed height)
 */
export const ValidateLayout: React.FC<ValidateLayoutProps> = ({ sidebar, livePanel, evidencePanel, trendsPanel }) => {
  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden"> 
      {/* 3-column main area */}
      <div className="flex-1 flex min-h-0 overflow-hidden">
        {/* Left sidebar */}
        <aside className="w-64 border-r border-white/10 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto">
            {sidebar}
          </div>
        </aside>

        {/* Center live verification */}
        <main className="flex-1 min-w-0 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto">
            {livePanel}
          </div>
        </main>

        {/* Right evidence */}
        <aside className="w-80 border-l border-white/10 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto">
            {evidencePanel}
          </div>
        </aside>
      </div>

      {/* Bottom trends */}
      <div className="h-64 border-t border-white/10 flex-shrink-0 overflow-hidden">
        <div className="h-full overflow-y-auto">
          {trendsPanel}
        </div>
      </div>
    </div>
  )
}

export default ValidateLayout

