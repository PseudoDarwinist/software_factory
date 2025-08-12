import { useMemo } from 'react'

export interface TrendPoint { t: Date; v: number }

export interface TrendsData {
  sla: TrendPoint[]
  accuracy: TrendPoint[]
  perfLatency: TrendPoint[]
  testPassRate: TrendPoint[]
  bugEscapeRate: TrendPoint[]
}

function generateTrend(days = 14, base = 80, noise = 10): TrendPoint[] {
  const now = Date.now()
  return Array.from({ length: days }, (_, i) => ({
    t: new Date(now - (days - i) * 24 * 3600 * 1000),
    v: base + (Math.random() * noise * 2 - noise)
  }))
}

export function useTrendsData(days: number): TrendsData {
  return useMemo(() => {
    return {
      sla: generateTrend(days, 92, 5),
      accuracy: generateTrend(days, 96, 2.5),
      perfLatency: generateTrend(days, 2100, 350), // ms
      testPassRate: generateTrend(days, 94, 4),
      bugEscapeRate: generateTrend(days, 1.5, 0.8), // per 1k
    }
  }, [days])
}

export function mean(series: TrendPoint[]): number {
  if (!series.length) return 0
  return series.reduce((s, p) => s + p.v, 0) / series.length
}

export function percentChange(current: number, previous: number): number {
  if (previous === 0) return 0
  return ((current - previous) / previous) * 100
}

export function linearForecastNext(series: TrendPoint[]): number {
  // Simple linear regression y = a + b*x where x=0..n-1
  const n = series.length
  if (n === 0) return 0
  const xs = series.map((_, i) => i)
  const ys = series.map(p => p.v)
  const sx = xs.reduce((s, x) => s + x, 0)
  const sy = ys.reduce((s, y) => s + y, 0)
  const sxx = xs.reduce((s, x) => s + x * x, 0)
  const sxy = xs.reduce((s, x, i) => s + x * ys[i], 0)
  const denom = n * sxx - sx * sx
  const b = denom !== 0 ? (n * sxy - sx * sy) / denom : 0
  const a = (sy - b * sx) / n
  const nextX = n
  return a + b * nextX
}

