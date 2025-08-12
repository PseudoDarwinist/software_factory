import React, { useMemo } from 'react'

export interface TrendPoint {
  t: Date
  v: number
}

interface TrendChartProps {
  title: string
  data: TrendPoint[]
  color?: string
  height?: number
}

export const TrendChart: React.FC<TrendChartProps> = ({ title, data, color = '#37B7F7', height = 160 }) => {
  const { pathD, minV, maxV } = useMemo(() => {
    if (!data || data.length === 0) return { pathD: '', minV: 0, maxV: 1 }
    const sorted = [...data].sort((a, b) => a.t.getTime() - b.t.getTime())
    const xs = sorted.map((p) => p.t.getTime())
    const ys = sorted.map((p) => p.v)
    const minX = Math.min(...xs)
    const maxX = Math.max(...xs)
    const minV = Math.min(...ys)
    const maxV = Math.max(...ys)
    const pad = 8
    const w = 600
    const h = height
    const scaleX = (x: number) => (w - pad * 2) * (x - minX) / Math.max(1, maxX - minX) + pad
    const scaleY = (y: number) => h - pad - (h - pad * 2) * (y - minV) / Math.max(1, maxV - minV)
    const d = sorted.map((p, i) => `${i === 0 ? 'M' : 'L'} ${scaleX(p.t.getTime()).toFixed(2)} ${scaleY(p.v).toFixed(2)}`).join(' ')
    return { pathD: d, minV, maxV }
  }, [data, height])

  return (
    <div>
      <div className="text-sm text-white/70 mb-2">{title}</div>
      <svg viewBox={`0 0 600 ${height}`} className="w-full" role="img" aria-label={title}>
        {/* grid */}
        <g opacity="0.15" stroke="#ffffff">
          {Array.from({ length: 4 }, (_, i) => (
            <line key={i} x1="0" x2="600" y1={(height * (i + 1) / 5).toFixed(0)} y2={(height * (i + 1) / 5).toFixed(0)} />
          ))}
        </g>
        {/* line */}
        <path d={pathD} fill="none" stroke={color} strokeWidth="2.5" />
      </svg>
      <div className="text-xs text-white/40">Range: {minV.toFixed(1)} – {maxV.toFixed(1)}</div>
    </div>
  )
}

export default TrendChart

