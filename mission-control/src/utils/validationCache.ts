import type { ValidationRun, ValidationCheck, ValidationEvidence } from '@/types/validation'

interface CacheEntry {
  run: ValidationRun | null
  checks: ValidationCheck[]
  evidenceByCheckId: Record<string, ValidationEvidence>
  ts: number
}

const CACHE = new Map<string, CacheEntry>()
const TTL_MS = 60_000 // 1 minute

export function get(projectId: string): Omit<CacheEntry, 'ts'> | null {
  const entry = CACHE.get(projectId)
  if (!entry) return null
  if (Date.now() - entry.ts > TTL_MS) {
    CACHE.delete(projectId)
    return null
  }
  const { ts, ...rest } = entry
  return rest
}

export function set(projectId: string, data: Omit<CacheEntry, 'ts'>): void {
  CACHE.set(projectId, { ...data, ts: Date.now() })
}

export function invalidate(projectId?: string): void {
  if (projectId) {
    CACHE.delete(projectId)
    return
  }
  CACHE.clear()
}

function ensure(projectId: string): CacheEntry {
  const existing = CACHE.get(projectId)
  if (existing) return existing
  const created: CacheEntry = { run: null, checks: [], evidenceByCheckId: {}, ts: Date.now() }
  CACHE.set(projectId, created)
  return created
}

export function mergeRun(projectId: string, run: Partial<ValidationRun> | null): void {
  const entry = ensure(projectId)
  entry.run = { ...(entry.run || ({} as any)), ...(run || {}) } as ValidationRun | null
  entry.ts = Date.now()
}

export function mergeChecks(projectId: string, updates: ValidationCheck[]): ValidationCheck[] {
  const entry = ensure(projectId)
  const byId = new Map<string, ValidationCheck>(entry.checks.map((c) => [c.id, c]))
  updates.forEach((u) => {
    const before = byId.get(u.id)
    byId.set(u.id, { ...(before || ({} as any)), ...u })
  })
  const next = Array.from(byId.values())
  entry.checks = next
  entry.ts = Date.now()
  return next
}

export function mergeEvidence(
  projectId: string,
  records: Array<{ checkId: string; evidence: Partial<ValidationEvidence> }>
): Record<string, ValidationEvidence> {
  const entry = ensure(projectId)
  for (const { checkId, evidence } of records) {
    const prev = entry.evidenceByCheckId[checkId] || {}
    entry.evidenceByCheckId[checkId] = { ...prev, ...(evidence || {}) }
  }
  entry.ts = Date.now()
  return { ...entry.evidenceByCheckId }
}

