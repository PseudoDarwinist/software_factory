import React, { useMemo, useState } from 'react'
import { TrendChart, type TrendPoint } from './TrendChart'
import { MetricCard } from './MetricCard'
import { GlassBackground } from '@/components/core/GlassBackground'
import { useTrendsData, mean, percentChange, linearForecastNext } from '@/hooks/useTrendsData'

interface TrendsDashboardProps {
  projectId?: string
}

function generateTrend(days = 14, base = 80, noise = 10): TrendPoint[] {
  const now = Date.now()
  return Array.from({ length: days }, (_, i) => ({
    t: new Date(now - (days - i) * 24 * 3600 * 1000),
    v: base + (Math.random() * noise * 2 - noise)
  }))
}

export const TrendsDashboard: React.FC<TrendsDashboardProps> = ({ projectId }) => {
  const [range, setRange] = useState<'7d' | '14d' | '30d'>('14d')
  const days = range === '7d' ? 7 : range === '30d' ? 30 : 14
  const data = useTrendsData(days)

  const latestSla = data.sla[data.sla.length - 1]?.v ?? 0
  const latestAcc = data.accuracy[data.accuracy.length - 1]?.v ?? 0
  const forecastAcc = linearForecastNext(data.accuracy)
  const slaChange = percentChange(latestSla, data.sla[0]?.v ?? latestSla)

  return (
    <div className="h-full grid grid-cols-2 gap-6">
      <GlassBackground className="p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="text-lg text-white font-semibold">SLA Pass-rate</div>
          <div className="flex items-center gap-2 text-xs">
            <button className={`px-2 py-1 rounded border ${range==='7d'?'bg-white/15 border-white/30':'bg-white/5 border-white/10'}`} onClick={() => setRange('7d')}>7d</button>
            <button className={`px-2 py-1 rounded border ${range==='14d'?'bg-white/15 border-white/30':'bg-white/5 border-white/10'}`} onClick={() => setRange('14d')}>14d</button>
            <button className={`px-2 py-1 rounded border ${range==='30d'?'bg-white/15 border-white/30':'bg-white/5 border-white/10'}`} onClick={() => setRange('30d')}>30d</button>
          </div>
        </div>
        <TrendChart title="Pass-rate (%)" data={data.sla} color="#10B981" />
      </GlassBackground>

      <div className="grid grid-rows-2 gap-6">
        <MetricCard label="Current SLA" value={`${latestSla.toFixed(1)}%`} sublabel={`Δ ${slaChange.toFixed(1)}% vs start • Target ≥ 95%`} intent={latestSla >= 95 ? 'good' : latestSla >= 90 ? 'warn' : 'bad'} />
        <GlassBackground className="p-4">
          <div className="text-lg text-white font-semibold mb-3">Template Accuracy</div>
          <TrendChart title="Accuracy (%)" data={data.accuracy} color="#60A5FA" height={120} />
          <div className="mt-2 text-xs text-white/60">Forecast next: {forecastAcc.toFixed(1)}%</div>
        </GlassBackground>
      </div>
    </div>
  )
}

export default TrendsDashboard

