/**
 * KanbanCleaner - Component for clearing completed tasks and failed jobs
 * 
 * This component provides a UI for cleaning up the kanban board by:
 * - Showing current status of tasks and jobs
 * - Clearing completed tasks (DONE status)
 * - Clearing failed Build phase jobs
 * - Clearing old completed jobs
 */

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { clsx } from 'clsx';
import { GlassBackground } from './GlassBackground';

interface KanbanStatus {
  task_counts: Record<string, number>;
  job_counts: Record<string, number>;
  clearable_items: {
    completed_tasks: number;
    failed_jobs: number;
    old_completed_jobs: number;
  };
  recent_activity: {
    task_updates_24h: number;
    job_updates_24h: number;
  };
  timestamp: string;
}

interface ClearResults {
  cleared_tasks: number;
  cleared_failed_jobs: number;
  cleared_old_jobs: number;
  backups_created: string[];
}

interface KanbanCleanerProps {
  onClose?: () => void;
  className?: string;
}

export const KanbanCleaner: React.FC<KanbanCleanerProps> = ({
  onClose,
  className
}) => {
  const [status, setStatus] = useState<KanbanStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [lastClearResults, setLastClearResults] = useState<ClearResults | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load current status
  const loadStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api/kanban/status');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      setStatus(data);
    } catch (err) {
      console.error('Failed to load kanban status:', err);
      setError(err instanceof Error ? err.message : 'Failed to load status');
    } finally {
      setLoading(false);
    }
  };

  // Clear kanban board
  const clearBoard = async (options: {
    clear_tasks?: boolean;
    clear_failed_jobs?: boolean;
    clear_old_jobs?: boolean;
  }) => {
    try {
      setClearing(true);
      setError(null);
      
      const response = await fetch('/api/kanban/clear', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(options),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        setLastClearResults(data.results);
        // Reload status to show updated counts
        await loadStatus();
      } else {
        throw new Error(data.error || 'Clear operation failed');
      }
    } catch (err) {
      console.error('Failed to clear kanban board:', err);
      setError(err instanceof Error ? err.message : 'Failed to clear board');
    } finally {
      setClearing(false);
    }
  };

  // Load status on mount
  useEffect(() => {
    loadStatus();
  }, []);

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const getTotalClearableItems = () => {
    if (!status) return 0;
    return (
      status.clearable_items.completed_tasks +
      status.clearable_items.failed_jobs +
      status.clearable_items.old_completed_jobs
    );
  };

  return (
    <div className={clsx('relative', className)}>
      <GlassBackground className="p-6 rounded-lg">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-white">Kanban Board Cleaner</h3>
            <p className="text-sm text-white/60">Clear completed tasks and failed jobs</p>
          </div>
          {onClose && (
            <button
              onClick={onClose}
              className="text-white/40 hover:text-white/60 transition-colors"
            >
              ✕
            </button>
          )}
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white/60"></div>
            <span className="ml-3 text-white/60">Loading status...</span>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-500/20 border border-red-500/30 rounded-lg p-4 mb-4">
            <div className="flex items-center">
              <span className="text-red-400 mr-2">⚠</span>
              <span className="text-red-300">{error}</span>
            </div>
          </div>
        )}

        {/* Status Display */}
        {status && !loading && (
          <div className="space-y-6">
            {/* Current Status */}
            <div>
              <h4 className="text-sm font-medium text-white/80 mb-3">Current Status</h4>
              <div className="grid grid-cols-2 gap-4">
                {/* Task Counts */}
                <div className="bg-white/5 rounded-lg p-3">
                  <h5 className="text-xs font-medium text-white/60 mb-2">Tasks</h5>
                  <div className="space-y-1">
                    {Object.entries(status.task_counts).map(([statusName, count]) => (
                      <div key={statusName} className="flex justify-between text-xs">
                        <span className="text-white/60 capitalize">{statusName}:</span>
                        <span className="text-white">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Job Counts */}
                <div className="bg-white/5 rounded-lg p-3">
                  <h5 className="text-xs font-medium text-white/60 mb-2">Jobs</h5>
                  <div className="space-y-1">
                    {Object.entries(status.job_counts).map(([statusName, count]) => (
                      <div key={statusName} className="flex justify-between text-xs">
                        <span className="text-white/60 capitalize">{statusName}:</span>
                        <span className="text-white">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Clearable Items */}
            <div>
              <h4 className="text-sm font-medium text-white/80 mb-3">Items Available for Clearing</h4>
              <div className="bg-white/5 rounded-lg p-4">
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-white/60">Completed tasks (DONE):</span>
                    <span className="text-white font-medium">{status.clearable_items.completed_tasks}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/60">Failed jobs (1+ hours old):</span>
                    <span className="text-white font-medium">{status.clearable_items.failed_jobs}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-white/60">Old completed jobs (7+ days):</span>
                    <span className="text-white font-medium">{status.clearable_items.old_completed_jobs}</span>
                  </div>
                  <div className="border-t border-white/10 pt-2 mt-2">
                    <div className="flex justify-between font-medium">
                      <span className="text-white/80">Total clearable items:</span>
                      <span className="text-white">{getTotalClearableItems()}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Clear Actions */}
            {getTotalClearableItems() > 0 && (
              <div>
                <h4 className="text-sm font-medium text-white/80 mb-3">Clear Actions</h4>
                <div className="space-y-3">
                  {/* Individual clear buttons */}
                  {status.clearable_items.completed_tasks > 0 && (
                    <button
                      onClick={() => clearBoard({ clear_tasks: true })}
                      disabled={clearing}
                      className="w-full bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 rounded-lg p-3 text-left transition-colors disabled:opacity-50"
                    >
                      <div className="flex justify-between items-center">
                        <span className="text-white">Clear completed tasks</span>
                        <span className="text-blue-300 text-sm">{status.clearable_items.completed_tasks} items</span>
                      </div>
                    </button>
                  )}

                  {status.clearable_items.failed_jobs > 0 && (
                    <button
                      onClick={() => clearBoard({ clear_failed_jobs: true })}
                      disabled={clearing}
                      className="w-full bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 rounded-lg p-3 text-left transition-colors disabled:opacity-50"
                    >
                      <div className="flex justify-between items-center">
                        <span className="text-white">Clear failed jobs</span>
                        <span className="text-red-300 text-sm">{status.clearable_items.failed_jobs} items</span>
                      </div>
                    </button>
                  )}

                  {status.clearable_items.old_completed_jobs > 0 && (
                    <button
                      onClick={() => clearBoard({ clear_old_jobs: true })}
                      disabled={clearing}
                      className="w-full bg-gray-500/20 hover:bg-gray-500/30 border border-gray-500/30 rounded-lg p-3 text-left transition-colors disabled:opacity-50"
                    >
                      <div className="flex justify-between items-center">
                        <span className="text-white">Clear old completed jobs</span>
                        <span className="text-gray-300 text-sm">{status.clearable_items.old_completed_jobs} items</span>
                      </div>
                    </button>
                  )}

                  {/* Clear all button */}
                  <button
                    onClick={() => clearBoard({ 
                      clear_tasks: true, 
                      clear_failed_jobs: true, 
                      clear_old_jobs: true 
                    })}
                    disabled={clearing}
                    className="w-full bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/30 rounded-lg p-3 text-left transition-colors disabled:opacity-50"
                  >
                    <div className="flex justify-between items-center">
                      <span className="text-white font-medium">Clear all items</span>
                      <span className="text-purple-300 text-sm">{getTotalClearableItems()} items</span>
                    </div>
                  </button>
                </div>
              </div>
            )}

            {/* No items to clear */}
            {getTotalClearableItems() === 0 && (
              <div className="bg-green-500/20 border border-green-500/30 rounded-lg p-4">
                <div className="flex items-center">
                  <span className="text-green-400 mr-2">✓</span>
                  <span className="text-green-300">No items need clearing - your kanban board is clean!</span>
                </div>
              </div>
            )}

            {/* Last Clear Results */}
            {lastClearResults && (
              <div className="bg-white/5 rounded-lg p-4">
                <h4 className="text-sm font-medium text-white/80 mb-2">Last Clear Results</h4>
                <div className="space-y-1 text-sm">
                  <div className="text-white/60">
                    Cleared {lastClearResults.cleared_tasks} tasks, {lastClearResults.cleared_failed_jobs} failed jobs, {lastClearResults.cleared_old_jobs} old jobs
                  </div>
                  {lastClearResults.backups_created.length > 0 && (
                    <div className="text-white/60">
                      Backups created: {lastClearResults.backups_created.join(', ')}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Clearing State */}
            {clearing && (
              <div className="bg-blue-500/20 border border-blue-500/30 rounded-lg p-4">
                <div className="flex items-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-400 mr-3"></div>
                  <span className="text-blue-300">Clearing items...</span>
                </div>
              </div>
            )}

            {/* Footer */}
            <div className="text-xs text-white/40 text-center">
              Last updated: {formatTime(status.timestamp)}
              <button
                onClick={loadStatus}
                className="ml-2 text-blue-400 hover:text-blue-300 transition-colors"
              >
                Refresh
              </button>
            </div>
          </div>
        )}
      </GlassBackground>
    </div>
  );
};

export default KanbanCleaner;