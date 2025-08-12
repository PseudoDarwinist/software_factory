/**
 * ReleaseProgressBar - Validation stage progress visualization
 * 
 * This component displays a horizontal progress bar with circular stage indicators
 * showing the current status of validation stages in the release pipeline.
 * Follows the same pattern as SourcesTrayCard progress bar but adapted for validation stages.
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { clsx } from 'clsx';

// Types for validation stages
export interface ValidationStage {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'success' | 'warning' | 'error';
  timestamp?: Date;
  duration?: number;
  description?: string;
}

interface ReleaseProgressBarProps {
  stages: ValidationStage[];
  onStageClick?: (stage: ValidationStage) => void;
  className?: string;
}

// Mock data generator for development
export const generateMockValidationStages = (): ValidationStage[] => [
  { 
    id: 'commit', 
    name: 'Commit', 
    status: 'success', 
    timestamp: new Date(Date.now() - 300000), 
    duration: 2000,
    description: 'Code committed and validated'
  },
  { 
    id: 'build', 
    name: 'Build', 
    status: 'success', 
    timestamp: new Date(Date.now() - 240000), 
    duration: 45000,
    description: 'Application built successfully'
  },
  { 
    id: 'test', 
    name: 'Test', 
    status: 'success', 
    timestamp: new Date(Date.now() - 180000), 
    duration: 120000,
    description: 'All tests passed'
  },
  { 
    id: 'security', 
    name: 'Security', 
    status: 'warning', 
    timestamp: new Date(Date.now() - 120000), 
    duration: 30000,
    description: 'Security scan completed with warnings'
  },
  { 
    id: 'deploy', 
    name: 'Deploy', 
    status: 'running', 
    timestamp: new Date(Date.now() - 60000),
    description: 'Deployment in progress'
  },
  { 
    id: 'monitor', 
    name: 'Monitor', 
    status: 'pending',
    description: 'Monitoring validation pending'
  },
  { 
    id: 'release', 
    name: 'Release', 
    status: 'pending',
    description: 'Release approval pending'
  }
];

// Helper functions for stage styling
const getStageIcon = (status: ValidationStage['status']) => {
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

const getStageColors = (status: ValidationStage['status']) => {
  switch (status) {
    case 'success':
      return {
        background: '#10B981', // green-500
        border: '#059669', // green-600
        shadow: '0 0 10px rgba(16, 185, 129, 0.8), 0 0 18px rgba(5, 150, 105, 0.4), 0 0 24px rgba(16, 185, 129, 0.2)',
        textColor: '#10B981'
      };
    case 'warning':
      return {
        background: '#F59E0B', // yellow-500
        border: '#D97706', // yellow-600
        shadow: '0 0 10px rgba(245, 158, 11, 0.8), 0 0 18px rgba(217, 119, 6, 0.4), 0 0 24px rgba(245, 158, 11, 0.2)',
        textColor: '#F59E0B'
      };
    case 'error':
      return {
        background: '#EF4444', // red-500
        border: '#DC2626', // red-600
        shadow: '0 0 10px rgba(239, 68, 68, 0.8), 0 0 18px rgba(220, 38, 38, 0.4), 0 0 24px rgba(239, 68, 68, 0.2)',
        textColor: '#EF4444'
      };
    case 'running':
      return {
        background: '#3B82F6', // blue-500
        border: '#2563EB', // blue-600
        shadow: '0 0 10px rgba(59, 130, 246, 0.8), 0 0 18px rgba(37, 99, 235, 0.4), 0 0 24px rgba(59, 130, 246, 0.2)',
        textColor: '#3B82F6'
      };
    default:
      return {
        background: '#6B7280', // gray-500
        border: '#4B5563', // gray-600
        shadow: 'none',
        textColor: '#9CA3AF' // gray-400
      };
  }
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

const formatTime = (date?: Date) => {
  if (!date) return '';
  return date.toLocaleTimeString('en-US', { 
    hour12: false, 
    hour: '2-digit', 
    minute: '2-digit' 
  });
};

export const ReleaseProgressBar: React.FC<ReleaseProgressBarProps> = ({
  stages,
  onStageClick,
  className
}) => {
  const [hoveredStage, setHoveredStage] = useState<string | null>(null);

  // Guard: coerce undefined to empty array to avoid runtime issues during live updates
  const safeStages = Array.isArray(stages) ? stages : []

  // Calculate progress percentage based on completed stages
  const completedStages = safeStages.filter(stage => 
    stage.status === 'success' || stage.status === 'warning' || stage.status === 'error'
  ).length;
  const progressPercentage = safeStages.length > 0 ? (completedStages / safeStages.length) * 100 : 0;

  // Check if any stage is currently running for animation effects
  const hasRunningStage = safeStages.some(stage => stage.status === 'running');

  return (
    <div className={clsx('relative', className)}>
      {/* Progress container */}
      <div className="relative flex items-center justify-between px-4 py-6">
        {/* Base progress line */}
        <div 
          className="absolute top-1/2 left-4 right-4 h-px -translate-y-1/2"
          style={{ 
            background: 'linear-gradient(90deg, rgba(255,255,255,0.18), rgba(255,255,255,0.04))' 
          }}
        />
        
        {/* Animated progress line overlay */}
        <div 
          className="absolute top-1/2 left-4 h-px -translate-y-1/2 transition-all duration-1000 ease-out"
          style={{ 
            background: 'linear-gradient(90deg, rgba(72, 224, 216, 0.9) 0%, rgba(16, 185, 129, 0.7) 50%, rgba(72, 224, 216, 0.9) 100%)',
            boxShadow: '0 0 12px rgba(72, 224, 216, 0.6), 0 0 24px rgba(16, 185, 129, 0.4)',
            width: `${Math.max(0, Math.min(100, progressPercentage))}%`,
            opacity: progressPercentage > 0 ? 1 : 0
          }}
        />
        
        {/* Flowing light effects during running stages */}
        {hasRunningStage && (
          <>
            {/* Primary flowing light */}
            <motion.div 
              className="absolute top-1/2 left-4 h-px -translate-y-1/2"
              style={{ 
                background: 'radial-gradient(ellipse 40px 6px, rgba(72, 224, 216, 1) 0%, rgba(72, 224, 216, 0) 100%)',
                width: '80px',
                height: '6px',
                filter: 'blur(1px)'
              }}
              animate={{
                x: ['0px', 'calc(100% + 200px)'],
                opacity: [0, 1, 1, 0]
              }}
              transition={{
                duration: 3,
                ease: 'easeInOut',
                repeat: Infinity,
                delay: 0
              }}
            />
            {/* Secondary flowing light */}
            <motion.div 
              className="absolute top-1/2 left-4 h-px -translate-y-1/2"
              style={{ 
                background: 'radial-gradient(ellipse 30px 4px, rgba(16, 185, 129, 0.8) 0%, rgba(16, 185, 129, 0) 100%)',
                width: '60px',
                height: '4px',
                filter: 'blur(0.5px)'
              }}
              animate={{
                x: ['0px', 'calc(100% + 200px)'],
                opacity: [0, 1, 1, 0]
              }}
              transition={{
                duration: 2.5,
                ease: 'easeInOut',
                repeat: Infinity,
                delay: 0.8
              }}
            />
            {/* Tertiary flowing light */}
            <motion.div 
              className="absolute top-1/2 left-4 h-px -translate-y-1/2"
              style={{ 
                background: 'radial-gradient(ellipse 25px 3px, rgba(72, 224, 216, 0.6) 0%, rgba(72, 224, 216, 0) 100%)',
                width: '50px',
                height: '3px',
                filter: 'blur(0.3px)'
              }}
              animate={{
                x: ['0px', 'calc(100% + 200px)'],
                opacity: [0, 1, 1, 0]
              }}
              transition={{
                duration: 2.2,
                ease: 'easeInOut',
                repeat: Infinity,
                delay: 1.5
              }}
            />
          </>
        )}
        
        {/* Stage indicators */}
        {safeStages.map((stage, index) => {
          const colors = getStageColors(stage.status);
          const isActive = stage.status !== 'pending';
          const isHovered = hoveredStage === stage.id;
          
          return (
            <div key={stage.id} className="relative flex flex-col items-center z-10">
              {/* Stage circle */}
              <motion.div
                className={clsx(
                  'w-8 h-8 rounded-full border-2 flex items-center justify-center text-white text-sm font-bold cursor-pointer transition-all duration-500 relative',
                  stage.status === 'running' && 'animate-pulse'
                )}
                style={{
                  background: colors.background,
                  borderColor: colors.border,
                  boxShadow: isActive ? colors.shadow : 'none'
                }}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.95 }}
                onMouseEnter={() => setHoveredStage(stage.id)}
                onMouseLeave={() => setHoveredStage(null)}
                onClick={() => onStageClick?.(stage)}
                title={`${stage.name} - ${stage.status}`}
              >
                {getStageIcon(stage.status)}
                
                {/* Pulsing ring for running stage */}
                {stage.status === 'running' && (
                  <div
                    className="absolute inset-0 rounded-full animate-ping"
                    style={{
                      background: 'transparent',
                      border: `1px solid ${colors.background}66`, // 40% opacity
                      transform: 'scale(1.5)'
                    }}
                  />
                )}
              </motion.div>
              
              {/* Stage label */}
              <span 
                className="text-xs mt-2 whitespace-nowrap transition-colors duration-300"
                style={{ 
                  color: isActive ? colors.textColor : '#9CA3AF',
                  textShadow: isActive ? `0 0 8px ${colors.background}66` : 'none'
                }}
              >
                {stage.name}
              </span>
              
              {/* Hover tooltip */}
              {isHovered && (
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.9 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.9 }}
                  className="absolute top-12 left-1/2 transform -translate-x-1/2 z-50 pointer-events-none"
                >
                  <div
                    className="p-3 rounded-lg shadow-lg max-w-xs"
                    style={{
                      background: 'rgba(12, 17, 25, 0.95)',
                      border: '1px solid rgba(255, 255, 255, 0.1)',
                      backdropFilter: 'blur(12px)'
                    }}
                  >
                    <div className="text-sm font-medium text-white mb-1">
                      {stage.name}
                    </div>
                    <div className="text-xs text-gray-300 mb-2">
                      Status: <span style={{ color: colors.textColor }}>{stage.status}</span>
                    </div>
                    {stage.description && (
                      <div className="text-xs text-gray-400 mb-2">
                        {stage.description}
                      </div>
                    )}
                    {stage.timestamp && (
                      <div className="text-xs text-gray-500">
                        {formatTime(stage.timestamp)}
                        {stage.duration && ` • ${formatDuration(stage.duration)}`}
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </div>
          );
        })}
      </div>
      

    </div>
  );
};