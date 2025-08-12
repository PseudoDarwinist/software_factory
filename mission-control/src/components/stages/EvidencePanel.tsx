import React, { useMemo, useState } from 'react'
import { GlassBackground } from '@/components/core/GlassBackground'
import type { ValidationCheck, ValidationEvidence } from '@/types/validation'
import { generateEvidenceFor } from '@/services/mock/MockValidationService'
import { LogViewer } from './evidence/LogViewer'
import { TestResultsViewer } from './evidence/TestResultsViewer'
import { ScreenshotViewer } from './evidence/ScreenshotViewer'
import { PerformanceMetricsViewer } from './evidence/PerformanceMetricsViewer'
import { ErrorDetailsViewer } from './evidence/ErrorDetailsViewer'
import { ActionButtons } from './evidence/ActionButtons'
import validationApi from '@/services/api/ValidationApiService'
import { getValidationPermissions, getCurrentUser } from '@/utils/permissions'
import { motion, AnimatePresence } from 'framer-motion'

interface EvidencePanelProps {
  selected?: ValidationCheck | null
  evidence?: ValidationEvidence
}

type Tab = 'logs' | 'tests' | 'screenshots' | 'performance' | 'errors'

export const EvidencePanel: React.FC<EvidencePanelProps> = ({ selected, evidence: liveEvidence }) => {
  const [activeTab, setActiveTab] = useState<Tab>('logs')
  const evidence: ValidationEvidence | null = useMemo(() => (liveEvidence ? liveEvidence : (selected ? generateEvidenceFor(selected) : null)), [selected, liveEvidence])
  const perms = getValidationPermissions()
  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-white/10">
        <h2 className="text-lg font-semibold text-white">Evidence</h2>
      </div>

      {!selected ? (
        <div className="flex-1 grid place-items-center text-white/50">
          Select a validation check to see evidence
        </div>
      ) : (
        <div className="flex-1 p-4">
          {/* Header */}
          <GlassBackground className="p-4 mb-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium text-white/80">{selected.name}</div>
                <motion.div
                  key={`${selected.id}-${selected.status}`}
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.15 }}
                  className="text-xs text-white/50"
                >
                  {selected.type} • {selected.status}
                </motion.div>
              </div>
              <div className="w-full max-w-lg">
                <ActionButtons
                  onApproveOverride={async (reason) => {
                    if (!evidence) return
                    const latest = await validationApi.getLatestRun(selected.projectId as any)
                    if (latest?.id) await validationApi.addDecision(latest.id, 'approve_override', reason, getCurrentUser() || undefined)
                  }}
                  onSendToBug={async (reason) => {
                    const latest = await validationApi.getLatestRun(selected.projectId as any)
                    if (latest?.id) await validationApi.addDecision(latest.id, 'send_to_bug', reason, getCurrentUser() || undefined)
                  }}
                  onReject={async (reason) => {
                    const latest = await validationApi.getLatestRun(selected.projectId as any)
                    if (latest?.id) await validationApi.addDecision(latest.id, 'reject', reason, getCurrentUser() || undefined)
                  }}
                  onRetry={async () => {
                    const latest = await validationApi.getLatestRun(selected.projectId as any)
                    if (latest?.id) await validationApi.addDecision(latest.id, 'retry', undefined, getCurrentUser() || undefined)
                  }}
                  canApprove={perms.canApproveValidation}
                  canOverride={perms.canOverrideValidation}
                  canRetry={perms.canRetryValidation}
                  canBug={perms.canCreateBug}
                  canReject={perms.canRejectValidation}
                />
              </div>
            </div>
          </GlassBackground>

          {/* Tabs (gated by permissions) */}
          {perms.canAccessEvidence ? (
            <div className="flex items-center gap-2 mb-3">
              {(['logs','tests','screenshots','performance','errors'] as Tab[]).map(t => (
                <button key={t} onClick={() => setActiveTab(t)} className={`px-3 py-1.5 text-sm rounded border ${activeTab === t ? 'bg:white/15 border-white/30' : 'bg-white/5 border-white/10 hover:bg-white/10'}`}>{t}</button>
              ))}
            </div>
          ) : (
            <div className="text-xs text-white/50 mb-3">You do not have permission to view evidence.</div>
          )}

          {/* Content */}
          <div>
            {perms.canAccessEvidence ? (
              <AnimatePresence mode="popLayout" initial={false}>
                {activeTab === 'logs' && (
                  <motion.div key="logs" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}>
                    <LogViewer logs={perms.canAccessLogs ? (evidence?.logs || []) : []} />
                  </motion.div>
                )}
                {activeTab === 'tests' && (
                  <motion.div key="tests" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}>
                    <TestResultsViewer results={evidence?.testResults || []} />
                  </motion.div>
                )}
                {activeTab === 'screenshots' && (
                  <motion.div key="screenshots" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}>
                    <ScreenshotViewer screenshots={evidence?.screenshots || []} />
                  </motion.div>
                )}
                {activeTab === 'performance' && (
                  <motion.div key="performance" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}>
                    <PerformanceMetricsViewer metrics={evidence?.performanceMetrics || []} />
                  </motion.div>
                )}
                {activeTab === 'errors' && (
                  <motion.div key="errors" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }}>
                    <ErrorDetailsViewer errors={[]} />
                  </motion.div>
                )}
              </AnimatePresence>
            ) : null}
          </div>
        </div>
      )}
    </div>
  )
}

export default EvidencePanel

