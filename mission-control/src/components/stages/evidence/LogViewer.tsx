import React, { useMemo, useState } from 'react'
import type { LogEntry } from '@/types/validation'
import { GlassBackground } from '@/components/core/GlassBackground'

interface LogViewerProps {
  logs: LogEntry[]
}

const levelColor = (level: LogEntry['level']) =>
  level === 'error' ? 'text-red-400' : level === 'warn' ? 'text-yellow-300' : 'text-white/70'

export const LogViewer: React.FC<LogViewerProps> = ({ logs }) => {
  const [query, setQuery] = useState('')
  const [level, setLevel] = useState<'all' | LogEntry['level']>('all')

  const filtered = useMemo(() => {
    let list = logs
    if (level !== 'all') list = list.filter(l => l.level === level)
    if (query.trim()) {
      const q = query.toLowerCase()
      list = list.filter(l => l.message.toLowerCase().includes(q))
    }
    return list
  }, [logs, query, level])

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <input
          className="bg-white/5 border border-white/10 rounded px-3 py-2 text-sm outline-none focus:border-white/20 flex-1"
          placeholder="Search logs..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select className="bg-white/5 border border-white/10 rounded px-2 py-2 text-sm" value={level} onChange={(e) => setLevel(e.target.value as any)}>
          <option value="all">all</option>
          <option value="info">info</option>
          <option value="warn">warn</option>
          <option value="error">error</option>
        </select>
      </div>
      <GlassBackground className="p-3">
        <div className="space-y-1 text-sm">
          {filtered.map((l, idx) => (
            <div key={idx} className="flex items-center gap-3">
              <span className="text-white/40 font-mono text-xs w-24">
                {new Date(l.timestamp).toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
              <span className={`text-xs ${levelColor(l.level)}`}>[{l.level}]</span>
              <span className="text-white/80 whitespace-pre-wrap">{l.message}</span>
            </div>
          ))}
          {filtered.length === 0 && <div className="text-white/50">No matching logs.</div>}
        </div>
      </GlassBackground>
    </div>
  )
}

export default LogViewer

