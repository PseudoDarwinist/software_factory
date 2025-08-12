import React from 'react'
import type { ValidationCheck } from '@/types/validation'
import { ValidationCheckItem } from './ValidationCheckItem'
import { useMemo, useState } from 'react'
import { ValidationFilterControls, type SortBy, type SortOrder } from './ValidationFilterControls'
import { AnimatePresence } from 'framer-motion'

interface LiveVerificationPanelProps {
  checks: ValidationCheck[]
  selectedId?: string
  onSelect: (id: string) => void
  evidenceByCheckId?: Record<string, any>
}


export const LiveVerificationPanel: React.FC<LiveVerificationPanelProps> = ({ checks, selectedId, onSelect, evidenceByCheckId = {} }) => {
  const [status, setStatus] = useState<ValidationCheck['status'] | 'all'>('all')
  const [types, setTypes] = useState<Array<ValidationCheck['type']>>(['test','deployment','monitoring','security','performance'])
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState<SortBy>('time')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')
  const [searchInEvidence, setSearchInEvidence] = useState(false)
  const [dateFrom, setDateFrom] = useState<string | null>(null)
  const [dateTo, setDateTo] = useState<string | null>(null)

  const filtered = useMemo(() => {
    let list = checks
    if (status !== 'all') list = list.filter(c => c.status === status)
    if (types.length) list = list.filter(c => types.includes(c.type))
    if (search.trim()) {
      const q = search.toLowerCase()
      list = list.filter(c => {
        const nameMatch = c.name.toLowerCase().includes(q) || c.type.toLowerCase().includes(q)
        if (!searchInEvidence) return nameMatch
        const ev = evidenceByCheckId[c.id]
        const logs = ev?.logs || []
        const tests = ev?.testResults || []
        const screenshots = ev?.screenshots || []
        const metrics = ev?.performanceMetrics || []
        const evidenceText = [
          ...logs.map((l: any) => `${l.level} ${l.message}`),
          ...tests.map((t: any) => `${t.name} ${t.status} ${t.errorMessage || ''}`),
          ...screenshots.map((s: any) => s.caption || ''),
          ...metrics.map((m: any) => `${m.name} ${m.value}${m.unit || ''}`),
        ].join(' ').toLowerCase()
        return nameMatch || evidenceText.includes(q)
      })
    }
    if (dateFrom) {
      const fromTs = Date.parse(dateFrom)
      if (!isNaN(fromTs)) list = list.filter(c => c.timestamp.getTime() >= fromTs)
    }
    if (dateTo) {
      const toTs = Date.parse(dateTo)
      if (!isNaN(toTs)) list = list.filter(c => c.timestamp.getTime() <= toTs)
    }
    return list
  }, [checks, status, types, search, searchInEvidence, dateFrom, dateTo, evidenceByCheckId])

  const sorted = useMemo(() => {
    const list = [...filtered]
    const dir = sortOrder === 'asc' ? 1 : -1
    list.sort((a, b) => {
      if (sortBy === 'time') return (a.timestamp.getTime() - b.timestamp.getTime()) * dir
      if (sortBy === 'duration') return ((a.duration || 0) - (b.duration || 0)) * dir
      if (sortBy === 'status') return (a.status.localeCompare(b.status)) * dir
      return 0
    })
    return list
  }, [filtered, sortBy, sortOrder])

  const grouped = useMemo(() => {
    const groups: Record<string, ValidationCheck[]> = {}
    for (const c of sorted) {
      const key = c.type
      if (!groups[key]) groups[key] = []
      groups[key].push(c)
    }
    return groups
  }, [sorted])

  const groupOrder: Array<ValidationCheck['type']> = ['test','deployment','monitoring','security','performance']

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="p-4 border-b border-white/10 space-y-3">
        <h2 className="text-lg font-semibold text-white">Live Verification</h2>
        <ValidationFilterControls
          status={status}
          setStatus={setStatus}
          types={types}
          setTypes={setTypes}
          search={search}
          setSearch={setSearch}
          sortBy={sortBy}
          setSortBy={setSortBy}
          sortOrder={sortOrder}
          setSortOrder={setSortOrder}
          searchInEvidence={searchInEvidence}
          setSearchInEvidence={setSearchInEvidence}
          dateFrom={dateFrom}
          setDateFrom={setDateFrom}
          dateTo={dateTo}
          setDateTo={setDateTo}
          onExport={() => {
            const header = ['id','name','type','status','timestamp','duration']
            const rows = sorted.map(c => [c.id, c.name, c.type, c.status, c.timestamp.toISOString(), String(c.duration ?? '')])
            const csv = [header, ...rows].map(r => r.map(v => `"${String(v).replace(/"/g,'""')}"`).join(',')).join('\n')
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = 'validation_checks.csv'
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            URL.revokeObjectURL(url)
          }}
        />
      </div>
      <div className="flex-1 overflow-y-auto">
        <div className="space-y-4 p-1">
          {groupOrder.filter(g => grouped[g]?.length).map(group => (
            <div key={group}>
              <div className="sticky top-0 z-10 px-2 py-1 text-xs uppercase tracking-wider text-white/50 bg-slate-900/60 backdrop-blur border-b border-white/5">{group}</div>
              <div className="space-y-1">
                <AnimatePresence initial={false}>
                  {grouped[group].map(check => (
                    <ValidationCheckItem key={check.id} check={check} selected={selectedId === check.id} onClick={onSelect} />
                  ))}
                </AnimatePresence>
              </div>
            </div>
          ))}
          {sorted.length === 0 && (
            <div className="text-white/50 text-sm p-4">No checks match the current filters.</div>
          )}
        </div>
      </div>
    </div>
  )
}

export default LiveVerificationPanel

