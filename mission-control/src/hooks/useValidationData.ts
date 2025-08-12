import { useEffect, useMemo, useRef, useState } from 'react'
import validationApi from '@/services/api/ValidationApiService'
import validationWS from '@/services/validation/validationWebSocket'
import type { ValidationCheck, ValidationRun, ValidationEvidence } from '@/types/validation'
import { get, set, invalidate, mergeChecks, mergeEvidence, mergeRun } from '@/utils/validationCache'
import { useMissionControlStore } from '@/stores/missionControlStore'

interface UseValidationDataOptions {
  projectId: string
  enableRealtime?: boolean
}

interface UseValidationDataReturn {
  latestRun: ValidationRun | null
  checks: ValidationCheck[]
  selectedCheckId: string | null
  setSelectedCheckId: (id: string | null) => void
  connection: { connected: boolean; connecting: boolean; error: string | null }
  refresh: () => Promise<void>
  evidenceByCheckId: Record<string, ValidationEvidence>
}

export function useValidationData(options: UseValidationDataOptions): UseValidationDataReturn {
  const { projectId, enableRealtime = true } = options
  const [latestRun, setLatestRun] = useState<ValidationRun | null>(null)
  const [checks, setChecks] = useState<ValidationCheck[]>([])
  const [selectedCheckId, setSelectedCheckId] = useState<string | null>(null)
  const [connection, setConnection] = useState({ connected: false, connecting: false, error: null as string | null })
  const [evidenceByCheckId, setEvidenceByCheckId] = useState<Record<string, ValidationEvidence>>({})
  const prevStatusRef = useRef<Record<string, ValidationCheck['status']>>({})
  const actions = useMissionControlStore((s) => s.actions)
  const prefs = useMissionControlStore((s) => s.notificationPrefs)

  const refresh = async () => {
    try {
      const cached = get(projectId)
      if (cached) {
        setLatestRun(cached.run)
        setChecks(cached.checks)
        setEvidenceByCheckId(cached.evidenceByCheckId || {})
      }
      const run = await validationApi.getLatestRun(projectId)
      setLatestRun(run)
      if (run?.checks) setChecks(run.checks)
      set(projectId, { run: run || null, checks: run?.checks || [], evidenceByCheckId })
    } catch (e) {
      // In case of auth error or stale cache, invalidate to force re-fetch later
      invalidate(projectId)
      throw e
    }
  }

  useEffect(() => {
    setChecks([])
    setLatestRun(null)
    setSelectedCheckId(null)
    refresh()
  }, [projectId])

  useEffect(() => {
    if (!enableRealtime) return
    let unsubChecks: (() => void) | null = null
    let unsubRuns: (() => void) | null = null
    let unsubStatus: (() => void) | null = null
    let unsubEvidence: (() => void) | null = null

    // Configure throttling for UI smoothness
    validationWS.setThrottle({ maxEventsPerSecond: 30, maxBatchSize: 50 })

    validationWS.connect().catch(() => {})
    unsubStatus = validationWS.onStatusChange((s) => setConnection({ connected: s.connected, connecting: s.connecting, error: s.error }))

    unsubChecks = validationWS.subscribe('validation.checks', (payload) => {
      // payload may be a single check or a batch
      const updates: ValidationCheck[] = (payload?.type === 'batch' ? payload.events : [payload]) as ValidationCheck[]
      setChecks((prev) => {
        const nextArr = mergeChecks(projectId, updates)
        // Notifications on status transitions
        nextArr.forEach((c) => {
          const prevStatus = prevStatusRef.current[c.id]
          if (prevStatus && prevStatus !== c.status) {
            const shouldToast = prefs.toastsEnabled && (
              (c.status === 'success' && prefs.showSuccess) ||
              (c.status === 'warning' && prefs.showWarnings) ||
              (c.status === 'error' && prefs.showErrors)
            )
            if (shouldToast) {
              actions.addNotification({
                id: `check-${c.id}-${Date.now()}`,
                type: c.status === 'success' ? 'success' : c.status === 'warning' ? 'warning' : 'error',
                title: `Validation ${c.status}`,
                message: `${c.name} is ${c.status}`,
                timestamp: new Date().toISOString(),
              })
            }
            try {
              if (prefs.browserNotifications && 'Notification' in window && Notification.permission === 'granted') {
                new Notification(`Validation ${c.status}`, { body: `${c.name}` })
              }
            } catch {}
          }
          prevStatusRef.current[c.id] = c.status
        })
        set(projectId, { run: latestRun, checks: nextArr, evidenceByCheckId })
        return nextArr
      })
    })

    unsubRuns = validationWS.subscribe('validation.runs', (payload) => {
      const run: ValidationRun = payload?.type === 'batch' ? payload.events[payload.events.length - 1] : payload
      if (run?.projectId === projectId) {
        setLatestRun((prev) => ({ ...(prev || ({} as any)), ...run }))
        mergeRun(projectId, run)
        if (run?.checks && run.checks.length) {
          const nextArr = mergeChecks(projectId, run.checks)
          setChecks(nextArr)
          set(projectId, { run, checks: nextArr, evidenceByCheckId })
        }
      }
    })

    // Invalidate cache if we receive a cross-stage transition away from validate
    const unsubPhase = validationWS.subscribe('phase.transition', (payload) => {
      const evt = payload?.type === 'batch' ? payload.events[payload.events.length - 1] : payload
      try {
        if (evt?.projectId === projectId && evt?.to && evt?.to !== 'validate') {
          invalidate(projectId)
        }
      } catch {}
    })

    unsubEvidence = validationWS.subscribe('validation.evidence', (payload) => {
      const events: Array<{ checkId: string; evidence: ValidationEvidence }> =
        payload?.type === 'batch' ? payload.events : [payload]
      setEvidenceByCheckId((prev) => {
        const merged = mergeEvidence(
          projectId,
          events.filter(Boolean).map((e) => ({ checkId: e.checkId, evidence: e.evidence || {} }))
        )
        set(projectId, { run: latestRun, checks, evidenceByCheckId: merged })
        return merged
      })
    })

    return () => {
      unsubChecks?.()
      unsubRuns?.()
      unsubStatus?.()
      unsubEvidence?.()
      unsubPhase?.()
    }
  }, [projectId, enableRealtime, prefs.toastsEnabled, prefs.showSuccess, prefs.showWarnings, prefs.showErrors, prefs.browserNotifications])

  useEffect(() => {
    if (!selectedCheckId && checks.length > 0) {
      setSelectedCheckId(checks[0].id)
    }
  }, [checks, selectedCheckId])

  return { latestRun, checks, selectedCheckId, setSelectedCheckId, connection, refresh, evidenceByCheckId }
}

export default useValidationData



