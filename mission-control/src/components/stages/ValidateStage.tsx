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
  const [validationStages, setValidationStages] = useState<ValidationStage[]>([]);
  const { latestRun, checks, selectedCheckId, setSelectedCheckId, connection, evidenceByCheckId } = useValidationData({
    projectId: selectedProject!,
    enableRealtime: true,
  })
  const actions = useMissionControlStore((s) => s.actions)

  // Generate validation stages from real data
  useEffect(() => {
    console.log('ValidateStage: latestRun changed:', latestRun);
    console.log('ValidateStage: checks changed:', checks);
    
    if (!latestRun) {
      setValidationStages([]);
      return;
    }

    // Create stages based on the validation run and checks
    const stages: ValidationStage[] = [
      {
        id: 'merge',
        name: 'PR Merged',
        status: 'success', // Always success since we have a validation run
        icon: 'GitMerge',
        timestamp: latestRun.startedAt
      },
      {
        id: 'tests',
        name: 'Tests',
        status: getStageStatusFromChecks(checks, 'test'),
        icon: 'TestTube',
        timestamp: getLatestTimestampFromChecks(checks, 'test')
      },
      {
        id: 'security',
        name: 'Security',
        status: getStageStatusFromChecks(checks, 'security'),
        icon: 'Shield',
        timestamp: getLatestTimestampFromChecks(checks, 'security')
      },
      {
        id: 'deploy',
        name: 'Deploy',
        status: getStageStatusFromChecks(checks, 'deployment'),
        icon: 'Rocket',
        timestamp: getLatestTimestampFromChecks(checks, 'deployment')
      },
      {
        id: 'monitor',
        name: 'Monitor',
        status: latestRun.status === 'completed' ? 'success' : 
                latestRun.status === 'failed' ? 'error' : 
                latestRun.status === 'running' ? 'running' : 'pending',
        icon: 'Activity',
        timestamp: latestRun.completedAt || undefined
      },
      {
        id: 'release',
        name: 'Release',
        status: latestRun.status === 'completed' ? 'success' : 'pending',
        icon: 'Package',
        timestamp: latestRun.status === 'completed' ? latestRun.completedAt : undefined
      }
    ];

    setValidationStages(stages);
  }, [latestRun, checks]);

  // Helper functions for stage status
  const getStageStatusFromChecks = (checks: ValidationCheck[], type: string): ValidationStage['status'] => {
    const typeChecks = checks.filter(c => c.type === type);
    if (typeChecks.length === 0) return 'pending';
    
    if (typeChecks.some(c => c.status === 'error' || c.status === 'failure')) return 'error';
    if (typeChecks.some(c => c.status === 'warning')) return 'warning';
    if (typeChecks.some(c => c.status === 'running' || c.status === 'pending')) return 'running';
    if (typeChecks.every(c => c.status === 'success')) return 'success';
    
    return 'pending';
  };

  const getLatestTimestampFromChecks = (checks: ValidationCheck[], type: string): string | undefined => {
    const typeChecks = checks.filter(c => c.type === type);
    if (typeChecks.length === 0) return undefined;
    
    return typeChecks
      .map(c => c.timestamp)
      .filter(Boolean)
      .sort()
      .pop();
  };

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
    <div className="h-full flex flex-col bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 overflow-hidden">
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



      {/* Show message when no real validation processes are found */}
      {latestRun && checks.length === 0 && (
        <div className="flex-1 flex items-center justify-center px-6 py-8">
          <div className="max-w-md mx-auto text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-slate-700/50 flex items-center justify-center">
              <span className="text-white/40 text-2xl">🔍</span>
            </div>
            <h3 className="text-lg font-medium text-white mb-2">No Validation Processes Found</h3>
            <p className="text-sm text-white/60 mb-4">
              This repository doesn't have any GitHub Actions workflows, tests, or deployment processes configured.
            </p>
            <div className="text-xs text-white/40 bg-slate-800/50 rounded p-3">
              <p className="mb-2">To see validation data here, add:</p>
              <ul className="text-left space-y-1">
                <li>• GitHub Actions workflows (.github/workflows/)</li>
                <li>• Automated tests (npm test, pytest, etc.)</li>
                <li>• Deployment configurations</li>
                <li>• Security scanning tools</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Release Progress Bar */}
      <div className="px-6 py-4 border-b border-white/10">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-white/60">Release</span>
          <div className="text-xs text-white/40">
            Ver.1.4v1.2 • Pull Request: {latestRun?.prNumber || '?'} • {latestRun?.branch || 'main'}
          </div>
        </div>
        <ReleaseProgressBar 
          stages={validationStages} 
          onStageClick={(stage) => {
            console.log('Stage clicked:', stage);
          }}
        />
      </div>

      {/* Main Content Area - only show ValidateLayout when there are checks */}
      {latestRun && checks.length > 0 ? (
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
      ) : null}
    </div>
  );
};
