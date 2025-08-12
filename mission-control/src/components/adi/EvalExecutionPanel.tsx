/**
 * Evaluation Execution Panel - Interface for running evaluations
 * 
 * This component provides:
 * - Eval set selection and execution interface
 * - Real-time eval results display
 * - Eval history and trend visualization
 * - Confidence metrics for deployment decisions
 * 
 * Requirements: 4.7
 */

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { adiApi } from '@/services/api/adiApi'
import type { EvalSet, EvalResult } from '@/types/adi'
import '@/styles/glass-background.css'

interface EvalExecutionPanelProps {
  onClose: () => void
}

export const EvalExecutionPanel: React.FC<EvalExecutionPanelProps> = ({ onClose }) => {
  const [evalSets, setEvalSets] = useState<EvalSet[]>([])
  const [selectedEvalSet, setSelectedEvalSet] = useState<EvalSet | null>(null)
  const [results, setResults] = useState<EvalResult[]>([])
  const [currentExecution, setCurrentExecution] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [executing, setExecuting] = useState(false)

  useEffect(() => {
    loadEvalSets()
  }, [])

  useEffect(() => {
    if (selectedEvalSet) {
      loadResults(selectedEvalSet.id)
    }
  }, [selectedEvalSet])

  const loadEvalSets = async () => {
    try {
      const sets = await adiApi.getEvalSets()
      setEvalSets(sets)
      if (sets.length > 0) {
        setSelectedEvalSet(sets[0])
      }
    } catch (error) {
      console.error('Failed to load eval sets:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadResults = async (evalSetId: string) => {
    try {
      const evalResults = await adiApi.getEvalResults(evalSetId)
      setResults(evalResults)
    } catch (error) {
      console.error('Failed to load eval results:', error)
    }
  }

  const executeEvalSet = async () => {
    if (!selectedEvalSet) return

    setExecuting(true)
    try {
      const executionId = await adiApi.executeEvalSet(selectedEvalSet.id)
      setCurrentExecution(executionId)
      
      // Poll for results
      pollExecution(executionId)
    } catch (error) {
      console.error('Failed to execute eval set:', error)
      setExecuting(false)
    }
  }

  const pollExecution = async (executionId: string) => {
    const pollInterval = setInterval(async () => {
      try {
        const result = await adiApi.getEvalExecution(executionId)
        
        if (result) {
          setResults(prev => [result, ...prev])
          setCurrentExecution(null)
          setExecuting(false)
          clearInterval(pollInterval)
        }
      } catch (error) {
        console.error('Failed to poll execution:', error)
        clearInterval(pollInterval)
        setExecuting(false)
      }
    }, 2000)

    // Stop polling after 5 minutes
    setTimeout(() => {
      clearInterval(pollInterval)
      setExecuting(false)
    }, 300000)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ready': return 'text-blue-400 bg-blue-500/20'
      case 'running': return 'text-yellow-400 bg-yellow-500/20'
      case 'completed': return 'text-green-400 bg-green-500/20'
      case 'failed': return 'text-red-400 bg-red-500/20'
      default: return 'text-gray-400 bg-gray-500/20'
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 0.9) return 'text-green-400'
    if (score >= 0.7) return 'text-yellow-400'
    return 'text-red-400'
  }

  const formatDuration = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / 60000)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    if (days > 0) return `${days}d ago`
    if (hours > 0) return `${hours}h ago`
    if (minutes > 0) return `${minutes}m ago`
    return 'Just now'
  }

  if (loading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center"
      >
        <div className="w-6 h-6 border-2 border-white/20 border-t-white/60 rounded-full animate-spin" />
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="glass-effect rounded-xl border border-white/20 max-w-6xl w-full max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-white/10">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-white">Evaluation Execution</h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/10 rounded-lg text-white/60 hover:text-white transition-colors"
            >
              ✕
            </button>
          </div>
          <p className="text-white/60 text-sm mt-2">
            Run evaluations to assess AI decision quality and deployment readiness
          </p>
        </div>

        {/* Content */}
        <div className="flex h-[calc(90vh-120px)]">
          {/* Left: Eval Sets */}
          <div className="w-1/3 border-r border-white/10 p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-white">Evaluation Sets</h3>
              <button
                onClick={executeEvalSet}
                disabled={!selectedEvalSet || executing}
                className="px-3 py-1.5 bg-blue-500 hover:bg-blue-600 disabled:bg-white/10 disabled:text-white/30 text-white rounded-lg text-sm font-medium transition-colors"
              >
                {executing ? 'Running...' : 'Run Eval'}
              </button>
            </div>

            <div className="space-y-2 overflow-y-auto">
              {evalSets.map(evalSet => (
                <motion.div
                  key={evalSet.id}
                  onClick={() => setSelectedEvalSet(evalSet)}
                  className={`p-3 rounded-lg cursor-pointer transition-all ${
                    selectedEvalSet?.id === evalSet.id
                      ? 'bg-blue-500/20 border border-blue-400/50'
                      : 'bg-white/5 hover:bg-white/10 border border-transparent'
                  }`}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-sm font-medium text-white">{evalSet.name}</h4>
                    <span className={`text-xs px-2 py-1 rounded ${getStatusColor(evalSet.status)}`}>
                      {evalSet.status}
                    </span>
                  </div>
                  
                  <p className="text-xs text-white/60 mb-2 line-clamp-2">
                    {evalSet.description}
                  </p>
                  
                  <div className="flex items-center justify-between text-xs text-white/60">
                    <span>{evalSet.domain}</span>
                    <span>{evalSet.testCases} tests</span>
                  </div>
                  
                  {evalSet.lastRun && (
                    <div className="text-xs text-white/40 mt-1">
                      Last run: {formatDuration(evalSet.lastRun)}
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          </div>

          {/* Right: Results */}
          <div className="flex-1 p-4">
            {selectedEvalSet ? (
              <div className="h-full flex flex-col">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium text-white">
                    Results: {selectedEvalSet.name}
                  </h3>
                  {executing && (
                    <div className="flex items-center space-x-2 text-yellow-400">
                      <div className="w-4 h-4 border-2 border-yellow-400/20 border-t-yellow-400 rounded-full animate-spin" />
                      <span className="text-sm">Executing evaluation...</span>
                    </div>
                  )}
                </div>

                <div className="flex-1 overflow-y-auto">
                  {results.length === 0 ? (
                    <div className="flex items-center justify-center h-full text-white/60">
                      <div className="text-center">
                        <div className="text-4xl mb-4">📊</div>
                        <p>No results yet. Run an evaluation to see results.</p>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {results.map(result => (
                        <motion.div
                          key={result.id}
                          className="p-4 bg-white/5 rounded-lg border border-white/10"
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                        >
                          <div className="flex items-center justify-between mb-3">
                            <div className="text-sm text-white/60">
                              {new Date(result.timestamp).toLocaleString()}
                            </div>
                            <div className="flex items-center space-x-4">
                              <div className="text-xs text-white/60">
                                {result.details.passed}/{result.details.total} passed
                              </div>
                            </div>
                          </div>

                          {/* Metrics */}
                          <div className="grid grid-cols-4 gap-4 mb-4">
                            <div className="text-center">
                              <div className={`text-lg font-semibold ${getScoreColor(result.accuracy)}`}>
                                {(result.accuracy * 100).toFixed(1)}%
                              </div>
                              <div className="text-xs text-white/60">Accuracy</div>
                            </div>
                            <div className="text-center">
                              <div className={`text-lg font-semibold ${getScoreColor(result.precision)}`}>
                                {(result.precision * 100).toFixed(1)}%
                              </div>
                              <div className="text-xs text-white/60">Precision</div>
                            </div>
                            <div className="text-center">
                              <div className={`text-lg font-semibold ${getScoreColor(result.recall)}`}>
                                {(result.recall * 100).toFixed(1)}%
                              </div>
                              <div className="text-xs text-white/60">Recall</div>
                            </div>
                            <div className="text-center">
                              <div className={`text-lg font-semibold ${getScoreColor(result.f1Score)}`}>
                                {(result.f1Score * 100).toFixed(1)}%
                              </div>
                              <div className="text-xs text-white/60">F1 Score</div>
                            </div>
                          </div>

                          {/* Failures */}
                          {result.details.failures.length > 0 && (
                            <div>
                              <h4 className="text-sm font-medium text-white mb-2">
                                Failures ({result.details.failures.length})
                              </h4>
                              <div className="space-y-2 max-h-32 overflow-y-auto">
                                {result.details.failures.slice(0, 3).map((failure, index) => (
                                  <div key={index} className="p-2 bg-red-500/10 border border-red-400/20 rounded text-xs">
                                    <div className="font-medium text-red-300">{failure.testCase}</div>
                                    <div className="text-red-200/80 mt-1">{failure.reason}</div>
                                  </div>
                                ))}
                                {result.details.failures.length > 3 && (
                                  <div className="text-xs text-white/60 text-center">
                                    +{result.details.failures.length - 3} more failures
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </motion.div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-white/60">
                <div className="text-center">
                  <div className="text-4xl mb-4">📋</div>
                  <p>Select an evaluation set to view results</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}