import React from 'react'
import { clsx } from 'clsx'
import { GlassBackground } from '@/components/core/GlassBackground'
import type { ValidationCheckStatus, ValidationCheckType } from '@/types/validation'

export type SortBy = 'time' | 'status' | 'duration'
export type SortOrder = 'asc' | 'desc'

interface ValidationFilterControlsProps {
  status: ValidationCheckStatus | 'all'
  setStatus: (s: ValidationCheckStatus | 'all') => void
  types: ValidationCheckType[]
  setTypes: (t: ValidationCheckType[]) => void
  search: string
  setSearch: (q: string) => void
  sortBy: SortBy
  setSortBy: (s: SortBy) => void
  sortOrder: SortOrder
  setSortOrder: (o: SortOrder) => void
  // Advanced options
  searchInEvidence?: boolean
  setSearchInEvidence?: (v: boolean) => void
  dateFrom?: string | null
  setDateFrom?: (v: string | null) => void
  dateTo?: string | null
  setDateTo?: (v: string | null) => void
  onExport?: () => void
}

const ALL_TYPES: ValidationCheckType[] = ['test', 'deployment', 'monitoring', 'security', 'performance']

export const ValidationFilterControls: React.FC<ValidationFilterControlsProps> = ({
  status,
  setStatus,
  types,
  setTypes,
  search,
  setSearch,
  sortBy,
  setSortBy,
  sortOrder,
  setSortOrder,
  searchInEvidence,
  setSearchInEvidence,
  dateFrom,
  setDateFrom,
  dateTo,
  setDateTo,
  onExport,
}) => {
  const toggleType = (t: ValidationCheckType) => {
    if (types.includes(t)) setTypes(types.filter(x => x !== t))
    else setTypes([...types, t])
  }

  return (
    <GlassBackground className="p-3">
      <div className="flex flex-wrap gap-3 items-center">
        {/* Search */}
        <input
          className="bg-white/5 border border-white/10 rounded px-3 py-2 text-sm outline-none focus:border-white/20"
          placeholder="Search checks..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {setSearchInEvidence && (
          <label className="flex items-center gap-2 text-xs text-white/70">
            <input type="checkbox" checked={!!searchInEvidence} onChange={(e) => setSearchInEvidence(e.target.checked)} />
            Search evidence
          </label>
        )}

        {/* Status filter */}
        <div className="flex items-center gap-2 text-sm">
          <span className="text-white/60">Status:</span>
          {(['all','running','success','warning','error','pending'] as const).map(s => (
            <button
              key={s}
              onClick={() => setStatus(s as any)}
              className={clsx('px-2 py-1 rounded border text-xs', status === s ? 'bg-white/15 border-white/30' : 'bg-white/5 border-white/10 hover:bg-white/10')}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Type chips */}
        <div className="flex items-center gap-2 text-sm">
          <span className="text-white/60">Type:</span>
          {ALL_TYPES.map(t => (
            <button
              key={t}
              onClick={() => toggleType(t)}
              className={clsx('px-2 py-1 rounded border text-xs', types.includes(t) ? 'bg-white/15 border-white/30' : 'bg-white/5 border-white/10 hover:bg-white/10')}
            >
              {t}
            </button>
          ))}
        </div>

        {/* Date range */}
        {setDateFrom && setDateTo && (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-white/60">From:</span>
            <input
              type="datetime-local"
              className="bg-white/5 border border-white/10 rounded px-2 py-1 text-xs"
              value={dateFrom || ''}
              onChange={(e) => setDateFrom(e.target.value || null)}
            />
            <span className="text-white/60">To:</span>
            <input
              type="datetime-local"
              className="bg-white/5 border border-white/10 rounded px-2 py-1 text-xs"
              value={dateTo || ''}
              onChange={(e) => setDateTo(e.target.value || null)}
            />
          </div>
        )}

        {/* Sort */}
        <div className="flex items-center gap-2 text-sm">
          <span className="text-white/60">Sort:</span>
          <select
            className="bg-white/5 border border-white/10 rounded px-2 py-1 text-xs"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortBy)}
          >
            <option value="time">time</option>
            <option value="status">status</option>
            <option value="duration">duration</option>
          </select>
          <button
            className="px-2 py-1 rounded border text-xs bg-white/5 border-white/10 hover:bg-white/10"
            onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
          >
            {sortOrder}
          </button>
        </div>

        {/* Export */}
        {onExport && (
          <button
            className="ml-auto px-3 py-2 rounded border text-xs bg-white/5 border-white/10 hover:bg-white/10"
            onClick={onExport}
          >
            Export CSV
          </button>
        )}
      </div>
    </GlassBackground>
  )
}

export default ValidationFilterControls

