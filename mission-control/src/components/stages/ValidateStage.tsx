/**
 * ValidateStage - Comprehensive Validation Dashboard
 * 
 * This component implements the Validate phase UI with:
 * - Release progress bar showing validation stages
 * - Left sidebar with running checks and review items
 * - Live verification panel with real-time validation checks
 * - Evidence panel for detailed validation results
 * - Trends dashboard for historical validation metrics
 * - Mock data support for development and testing
 */

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { clsx } from 'clsx';
import { GlassBackground } from '@/components/core/GlassBackground';
import { ReleaseProgressBar, generateMockValidationStages, type ValidationStage } from './ReleaseProgressBar';

// Types for validation data

interface ValidationCheck {
  id: string;
  name: string;
  type: 'test' | 'deployment' | 'monitoring' | 'security' | 'performance';
  status: 'pending' | 'running' | 'success' | 'warning' | 'error';
  timestamp: Date;
  duration?: number;
  progress?: number;
  metadata: Record<string, any>;
}

interface ValidateStageProps {
  selectedProject: string | null;
  onStageChange?: (stage: string) => void;
}



const generateMockValidationChecks = (): ValidationCheck[] => [
  {
    id: '1',
    name: 'All -mtegration suite',
    type: 'test',
    status: 'success',
    timestamp: new Date(Date.now() - 180000),
    duration: 120000,
    progress: 100,
    metadata: { passRate: '100%', tests: 45 }
  },
  {
    id: '2',
    name: 'IROPS regression replay',
    type: 'test',
    status: 'success',
    timestamp: new Date(Date.now() - 150000),
    duration: 90000,
    progress: 100,
    metadata: { passRate: '42/43', coverage: '94%' }
  },
  {
    id: '3',
    name: 'Delay email SLA check',
    type: 'monitoring',
    status: 'warning',
    timestamp: new Date(Date.now() - 120000),
    duration: 30000,
    progress: 100,
    metadata: { sla: 'late', threshold: '5min' }
  },
  {
    id: '4',
    name: 'Gate-Change Template eval',
    type: 'deployment',
    status: 'success',
    timestamp: new Date(Date.now() - 90000),
    duration: 45000,
    progress: 100,
    metadata: { accuracy: '98%' }
  },
  {
    id: '5',
    name: 'Performance budgets',
    type: 'performance',
    status: 'running',
    timestamp: new Date(Date.now() - 30000),
    progress: 75,
    metadata: { currentMetric: 'Load time', target: '2s' }
  }
];

export const ValidateStage: React.FC<ValidateStageProps> = ({
  selectedProject,
  onStageChange,
}) => {
  const [validationStages] = useState<ValidationStage[]>(generateMockValidationStages());
  const [validationChecks] = useState<ValidationCheck[]>(generateMockValidationChecks());
  const [selectedCheck, setSelectedCheck] = useState<ValidationCheck | null>(null);

  // Auto-select first check on mount
  useEffect(() => {
    if (validationChecks.length > 0 && !selectedCheck) {
      setSelectedCheck(validationChecks[0]);
    }
  }, [validationChecks, selectedCheck]);



  const getCheckStatusIcon = (status: ValidationCheck['status']) => {
    switch (status) {
      case 'success':
        return '✓';
      case 'warning':
        return '⚠';
      case 'error':
        return '✗';
      case 'running':
        return '⟳';
      default:
        return '○';
    }
  };

  const getCheckStatusColor = (status: ValidationCheck['status']) => {
    switch (status) {
      case 'success':
        return 'text-green-400';
      case 'warning':
        return 'text-yellow-400';
      case 'error':
        return 'text-red-400';
      case 'running':
        return 'text-blue-400';
      default:
        return 'text-gray-400';
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const formatDuration = (ms?: number) => {
    if (!ms) return '';
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`;
    }
    return `${seconds}s`;
  };

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
        <div className="text-sm text-white/40 font-mono tracking-wider">SOFTWARE FACTORY</div>
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
            // TODO: Implement stage navigation
          }}
        />
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex">
        {/* Left Sidebar */}
        <div className="w-64 border-r border-white/10 flex flex-col">
          {/* Running Section */}
          <div className="p-4">
            <h3 className="text-lg font-semibold text-white mb-2">Running</h3>
            <p className="text-sm text-white/60 mb-4">No running checks</p>
            
            {/* Review Section */}
            <h3 className="text-lg font-semibold text-white mb-2">Review</h3>
            <div className="space-y-2">
              <div className="flex items-center space-x-2 text-sm">
                <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                <span className="text-white/80">Delay email SLA check</span>
              </div>
              <div className="flex items-center space-x-2 text-sm">
                <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                <span className="text-white/80">Gate-Change Template eval</span>
              </div>
            </div>
          </div>
        </div>

        {/* Center - Live Verification Panel */}
        <div className="flex-1 flex flex-col">
          <div className="p-4 border-b border-white/10">
            <h2 className="text-lg font-semibold text-white">Live Verification</h2>
          </div>
          
          <div className="flex-1 overflow-y-auto">
            <div className="space-y-1">
              {validationChecks.map((check) => (
                <motion.div
                  key={check.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={clsx(
                    'flex items-center justify-between p-3 cursor-pointer transition-all duration-200',
                    'hover:bg-white/5 border-l-2',
                    selectedCheck?.id === check.id 
                      ? 'bg-white/10 border-l-blue-400' 
                      : 'border-l-transparent'
                  )}
                  onClick={() => setSelectedCheck(check)}
                >
                  <div className="flex items-center space-x-3">
                    <span className="text-xs text-white/40 font-mono w-12">
                      {formatTime(check.timestamp)}
                    </span>
                    <span className="text-white/80">{check.name}</span>
                    {check.status === 'success' && check.metadata.passRate && (
                      <span className="text-xs text-green-400">{check.metadata.passRate}</span>
                    )}
                  </div>
                  <div className="flex items-center space-x-2">
                    {check.status === 'warning' && (
                      <span className="text-xs text-yellow-400 bg-yellow-400/10 px-2 py-1 rounded">
                        late
                      </span>
                    )}
                    <span className={clsx('text-lg', getCheckStatusColor(check.status))}>
                      {getCheckStatusIcon(check.status)}
                    </span>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>

        {/* Right - Evidence Panel */}
        <div className="w-80 border-l border-white/10 flex flex-col">
          <div className="p-4 border-b border-white/10">
            <h2 className="text-lg font-semibold text-white">Evidence</h2>
          </div>
          
          {selectedCheck && (
            <div className="flex-1 p-4">
              <GlassBackground className="p-4 mb-4">
                <div className="mb-4">
                  <h3 className="text-sm font-medium text-white/60 mb-1">Decision log</h3>
                  <div className="text-yellow-400 font-medium">O1287 - fullstring json</div>
                </div>
                
                <div className="grid grid-cols-2 gap-4 text-xs mb-4">
                  <div>
                    <div className="text-white/60 mb-1">Expected</div>
                    <div className="text-white/80">Outcome</div>
                  </div>
                  <div>
                    <div className="text-white/60 mb-1">Gate change</div>
                    <div className="text-white/80">Not mentioned</div>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <button className="w-full bg-green-500/20 border border-green-500/30 text-green-400 py-2 px-4 rounded-lg text-sm font-medium hover:bg-green-500/30 transition-colors">
                    ✓ Approve Override
                  </button>
                  <button className="w-full bg-blue-500/20 border border-blue-500/30 text-blue-400 py-2 px-4 rounded-lg text-sm font-medium hover:bg-blue-500/30 transition-colors">
                    🐛 Send to Bug Tracking
                  </button>
                </div>
              </GlassBackground>
            </div>
          )}
        </div>
      </div>

      {/* Bottom - Trends Dashboard */}
      <div className="h-64 border-t border-white/10 p-4">
        <GlassBackground className="h-full p-4">
          <h3 className="text-lg font-semibold text-white mb-4">Trends</h3>
          <div className="grid grid-cols-2 gap-6 h-full">
            {/* SLA Pass-rate Chart */}
            <div>
              <h4 className="text-sm text-white/60 mb-2">SLA Pass-rate</h4>
              <div className="h-24 bg-gradient-to-r from-green-500/20 to-blue-500/20 rounded relative overflow-hidden">
                {/* Mock chart bars */}
                <div className="absolute bottom-0 left-0 w-full h-full flex items-end space-x-1 p-2">
                  {Array.from({ length: 20 }, (_, i) => (
                    <div
                      key={i}
                      className="flex-1 bg-green-400/60 rounded-sm"
                      style={{ height: `${Math.random() * 80 + 20}%` }}
                    />
                  ))}
                </div>
              </div>
            </div>
            
            {/* Template Accuracy */}
            <div>
              <h4 className="text-sm text-white/60 mb-2">Template Accuracy</h4>
              <div className="flex items-center justify-between">
                <button className="bg-green-500/20 border border-green-500/30 text-green-400 py-2 px-4 rounded-lg text-sm font-medium hover:bg-green-500/30 transition-colors">
                  ✓ Approve Override
                </button>
                <button className="bg-blue-500/20 border border-blue-500/30 text-blue-400 py-2 px-4 rounded-lg text-sm font-medium hover:bg-blue-500/30 transition-colors">
                  🔄 Retry with Debug Mode
                </button>
              </div>
            </div>
          </div>
        </GlassBackground>
      </div>
    </div>
  );
};
