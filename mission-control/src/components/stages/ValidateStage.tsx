/**
 * ValidateStage - Comprehensive Validation Dashboard
 * 
 * This component implements the Validate phase UI with:
 * - Release progress bar showing validation stages
 * - Left sidebar with running checks and review items
 * - Live verification panel with real-time validation checks
 * - Evidence panel for detailed validation results
 * - Trends dashboard for historical validation metrics
 */

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { clsx } from 'clsx';
import { GlassBackground } from '@/components/core/GlassBackground';
import { ReleaseProgressBar, generateMockValidationStages, type ValidationStage } from './ReleaseProgressBar';
import { ValidateLayout } from './ValidateLayout';
import { LeftSidebar } from './LeftSidebar';
import { LiveVerificationPanel } from './LiveVerificationPanel';
import { EvidencePanel } from './EvidencePanel';
import { TrendsPanel } from './TrendsPanel';
import type { ValidationCheck as SharedValidationCheck } from '@/types/validation'
import useValidationData from '@/hooks/useValidationData'
import { useMissionControlStore } from '@/stores/missionControlStore'

// Types for validation data

type ValidationCheck = SharedValidationCheck

interface ValidateStageProps {
  selectedProject: string | null;
  onStageChange?: (stage: string) => void;
}

export const ValidateStage: React.FC<ValidateStageProps> = ({
  selectedProject,
  onStageChange,
}) => {
  const [validationStages, setValidationStages] = useState<ValidationStage[]>(generateMockValidationStages());
  const { latestRun, checks, selectedCheckId, setSelectedCheckId, connection, evidenceByCheckId } = useValidationData({
    projectId: selectedProject!,
    enableRealtime: true,
  })
  const actions = useMissionControlStore((s) => s.actions)

  // Connection status notifications
  useEffect(() => {
    if (connection.error) {
      actions.addNotification({
        id: `ws-${Date.now()}`,
        type: 'warning',
        title: 'Realtime connection',
        message: connection.error,
        timestamp: new Date().toISOString(),
      })
    }
  }, [connection.error])

  // Map latest run status to progress bar stages
  useEffect(() => {
    if (!latestRun) return
    setValidationStages(prev => {
      const next = [...prev]
      const byId = new Map(next.map(s => [s.id, s]))
      const setStatus = (id: string, status: ValidationStage['status']) => {
        const st = byId.get(id)
        if (st) st.status = status
      }
      // Reset dynamic stages to pending by default
      ;['security','deploy','monitor','release'].forEach(id => setStatus(id, 'pending'))
      switch (latestRun.status) {
        case 'running':
          setStatus('deploy', 'running')
          setStatus('monitor', 'pending')
          break
        case 'completed':
          setStatus('monitor', 'success')
          setStatus('release', 'success')
          break
        case 'failed':
          setStatus('release', 'error')
          break
        case 'blocked':
          setStatus('security', 'warning')
          break
        default:
          // pending -> leave defaults
          break
      }
      return Array.from(byId.values())
    })
  }, [latestRun])

  if (!selectedProject) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center text-white/60">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-white/5 flex items-center justify-center">
            <span className="text-white/40 text-2xl">✅</span>
          </div>
          <h3 className="text-lg font-medium mb-2">Validate Stage</h3>
          <p className="text-sm">Select a project to view validation dashboard</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header with VALIDATE title and SOFTWARE FACTORY */}
      <div className="flex items-center justify-between p-6 border-b border-white/10">
        <h1 className="text-2xl font-bold text-white tracking-wide">VALIDATE</h1>
        <div className="flex items-center gap-3">
          <span className={`text-xs ${connection.connected ? 'text-green-400' : connection.connecting ? 'text-amber-400' : 'text-red-400'}`}>
            {connection.connected ? 'WS Connected' : connection.connecting ? 'WS Connecting' : 'WS Disconnected'}
          </span>
          <div className="text-sm text-white/40 font-mono tracking-wider">SOFTWARE FACTORY</div>
        </div>
      </div>

      {/* Release Progress Bar */}
      <div className="px-6 py-4 border-b border-white/10">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-white/60">Release</span>
          <div className="text-xs text-white/40">
            Ver.1.4v1.2 • Pull Request: 1 +1 • main
          </div>
        </div>
        <ReleaseProgressBar 
          stages={validationStages} 
          onStageClick={(stage) => {
            console.log('Stage clicked:', stage);
          }}
        />
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex">
        {/* Left Sidebar */}
         <ValidateLayout 
          sidebar={
            <LeftSidebar 
               runningCount={checks.filter(c => c.status === 'running').length}
               reviewItems={checks
                .filter(c => c.status === 'warning' || c.status === 'error')
                .slice(0, 5)
                .map(c => ({ id: c.id, title: c.name, severity: c.status === 'warning' ? 'warning' : 'error' }))}
            />
          }
          livePanel={
            <LiveVerificationPanel 
               checks={checks}
               selectedId={selectedCheckId || undefined}
               onSelect={(id) => setSelectedCheckId(id)}
               evidenceByCheckId={evidenceByCheckId}
            />
          }
           evidencePanel={<EvidencePanel selected={checks.find(c => c.id === selectedCheckId) || null} evidence={selectedCheckId ? evidenceByCheckId[selectedCheckId] : undefined} />}
          trendsPanel={<TrendsPanel />}
        />
      </div>
    </div>
  );
};
