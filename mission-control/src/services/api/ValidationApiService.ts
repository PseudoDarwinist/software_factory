import missionControlApi from './missionControlApi'
import type { ValidationRun, ValidationCheck, ValidationEvidence } from '@/types/validation'
import { normalizeRun, normalizeCheck, normalizeEvidence } from '@/utils/validationTransform'

/**
 * Thin wrapper around missionControlApi for validation domain, with
 * normalized types and simple helpers.
 */
export class ValidationApiService {
  private async withRetry<T>(fn: () => Promise<T>, retries = 2, baseDelayMs = 300): Promise<T> {
    try {
      return await fn()
    } catch (e) {
      if (retries <= 0) throw e
      const attempt = 3 - retries
      const delay = baseDelayMs * Math.pow(2, attempt)
      await new Promise((r) => setTimeout(r, delay))
      return this.withRetry(fn, retries - 1, baseDelayMs)
    }
  }
  async getLatestRun(projectId: string): Promise<ValidationRun | null> {
    const data = await this.withRetry(() => missionControlApi.getLatestValidationRun(projectId))
    return data ? normalizeRun(data) : null
  }

  async getActiveRuns(projectId: string): Promise<ValidationRun[]> {
    const data = await this.withRetry(() => missionControlApi.getActiveValidationRuns(projectId))
    return (data?.active_validation_runs ?? []).map(normalizeRun)
  }

  async getRuns(projectId: string, params?: { limit?: number; status?: string }): Promise<{
    validation_runs: ValidationRun[]
    total: number
  }> {
    const res = await this.withRetry(() => missionControlApi.getValidationRuns(projectId, params))
    return { validation_runs: (res?.validation_runs ?? []).map(normalizeRun), total: res?.total ?? 0 }
  }

  async getRun(runId: string): Promise<ValidationRun | null> {
    const data = await this.withRetry(() => missionControlApi.getValidationRun(runId))
    return data ? normalizeRun(data) : null
  }

  async getChecksForRun(runId: string): Promise<ValidationCheck[]> {
    const run = await this.getRun(runId)
    return Array.isArray(run?.checks) ? run!.checks!.map((c) => normalizeCheck(c)) : []
  }

  // Retrieve evidence either from the run payload (if embedded) or via dedicated endpoint when available
  async getEvidenceForCheck(runId: string, checkId: string): Promise<ValidationEvidence | null> {
    // First attempt: fetch run and extract embedded evidence if present
    const run = await this.getRun(runId)
    const check = run?.checks?.find((c) => c.id === checkId)
    if (check?.evidence) return check.evidence

    // Fallback: attempt a dedicated API if backend adds it later; ignore 404s gracefully
    try {
      const raw = await this.withRetry(async () => {
        // @ts-expect-error Potential future endpoint; missionControlApi may add later
        return (missionControlApi as any).getValidationEvidence
          ? await (missionControlApi as any).getValidationEvidence(runId, checkId)
          : null
      })
      return raw ? normalizeEvidence(raw) : null
    } catch (err: any) {
      return null
    }
  }

  async addDecision(
    runId: string,
    action: 'approve_override' | 'send_to_bug' | 'reject' | 'retry',
    reason?: string,
    user?: string
  ): Promise<{ message: string; decisions: any[] }> {
    return this.withRetry(() => missionControlApi.addValidationDecision(runId, action, reason, user))
  }
}

export const validationApi = new ValidationApiService()
export default validationApi

