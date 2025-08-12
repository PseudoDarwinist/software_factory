/**
 * Domain Context Pane - Shows policy and similar cases
 * 
 * This component displays:
 * - Domain policies and rules relevant to the selected case
 * - Similar cases with their outcomes
 * - Domain knowledge and context information
 * - Analytics and trends for the domain
 * 
 * Requirements: 4.1
 */

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { adiApi } from '@/services/api/adiApi'
import type { DecisionCase, PolicyRule, SimilarCase, DomainMetrics } from '@/types/adi'

interface DomainContextPaneProps {
  selectedCase: DecisionCase | null
}

type ContextTab = 'policies' | 'similar' | 'metrics'

export const DomainContextPane: React.FC<DomainContextPaneProps> = ({ selectedCase }) => {
  const [activeTab, setActiveTab] = useState<ContextTab>('policies')
  const [policies, setPolicies] = useState<PolicyRule[]>([])
  const [similarCases, setSimilarCases] = useState<SimilarCase[]>([])
  const [metrics, setMetrics] = useState<DomainMetrics | null>(null)
  const [loading, setLoading] = useState(false)

  // Load context data when case changes
  useEffect(() => {
    if (selectedCase) {
      loadContextData()
    }
  }, [selectedCase])

  const loadContextData = async () => {
    if (!selectedCase) return

    setLoading(true)
    try {
      const [policiesData, similarData, metricsData] = await Promise.all([
        adiApi.getPolicyRules(selectedCase.domain),
        adiApi.getSimilarCases(selectedCase.id),
        adiApi.getDomainMetrics(selectedCase.domain)
      ])
      
      setPolicies(policiesData)
      setSimilarCases(similarData)
      setMetrics(metricsData)
    } catch (error) {
      console.error('Failed to load context data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (!selectedCase) {
    return (
      <div className="h-full flex items-center justify-center bg-white/5">
        <div className="text-center text-white/60">
          <div className="text-4xl mb-4">🎯</div>
          <p>Select a case to view domain context</p>
        </div>
      </div>
    )
  }

  const tabs: Array<{ id: ContextTab; label: string; icon: string }> = [
    { id: 'policies', label: 'Policies', icon: '📋' },
    { id: 'similar', label: 'Similar Cases', icon: '🔍' },
    { id: 'metrics', label: 'Metrics', icon: '📊' }
  ]

  const getSimilarityColor = (similarity: number) => {
    if (similarity >= 0.8) return 'text-green-400'
    if (similarity >= 0.6) return 'text-yellow-400'
    return 'text-red-400'
  }

  const getOutcomeIcon = (outcome: string) => {
    switch (outcome) {
      case 'correct': return '✅'
      case 'incorrect': return '❌'
      default: return '❓'
    }
  }

  const renderPolicies = () => (
    <div className="space-y-3">
      {policies.length === 0 ? (
        <div className="text-center text-white/60 py-8">
          <div className="text-2xl mb-2">📋</div>
          <p>No policies found for this domain</p>
        </div>
      ) : (
        policies.map(policy => (
          <motion.div
            key={policy.id}
            className="p-3 bg-white/5 rounded-lg border border-white/10"
            whileHover={{ backgroundColor: 'rgba(255,255,255,0.1)' }}
          >
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-white">{policy.name}</h4>
              <div className="flex items-center space-x-2">
                <span className={`text-xs px-2 py-1 rounded ${
                  policy.active ? 'bg-green-500/20 text-green-300' : 'bg-gray-500/20 text-gray-300'
                }`}>
                  {policy.active ? 'Active' : 'Inactive'}
                </span>
                <span className="text-xs text-white/60">P{policy.priority}</span>
              </div>
            </div>
            
            <div className="text-xs text-white/80 mb-2">
              <strong>Condition:</strong> {policy.condition}
            </div>
            
            <div className="text-xs text-white/80">
              <strong>Action:</strong> {policy.action}
            </div>
          </motion.div>
        ))
      )}
    </div>
  )

  const renderSimilarCases = () => (
    <div className="space-y-3">
      {similarCases.length === 0 ? (
        <div className="text-center text-white/60 py-8">
          <div className="text-2xl mb-2">🔍</div>
          <p>No similar cases found</p>
        </div>
      ) : (
        similarCases.map(similarCase => (
          <motion.div
            key={similarCase.id}
            className="p-3 bg-white/5 rounded-lg border border-white/10"
            whileHover={{ backgroundColor: 'rgba(255,255,255,0.1)' }}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <span className="text-lg">{getOutcomeIcon(similarCase.outcome)}</span>
                <span className={`text-xs font-mono ${getSimilarityColor(similarCase.similarity)}`}>
                  {(similarCase.similarity * 100).toFixed(1)}%
                </span>
              </div>
              <span className="text-xs text-white/60">
                {new Date(similarCase.timestamp).toLocaleDateString()}
              </span>
            </div>
            
            <div className="text-sm text-white/80 line-clamp-3">
              {similarCase.decision}
            </div>
          </motion.div>
        ))
      )}
    </div>
  )

  const renderMetrics = () => {
    if (!metrics) {
      return (
        <div className="text-center text-white/60 py-8">
          <div className="text-2xl mb-2">📊</div>
          <p>Loading metrics...</p>
        </div>
      )
    }

    return (
      <div className="space-y-4">
        {/* Overview Stats */}
        <div className="grid grid-cols-2 gap-3">
          <div className="p-3 bg-white/5 rounded-lg">
            <div className="text-xs text-white/60">Total Cases</div>
            <div className="text-lg font-semibold text-white">{metrics.totalCases}</div>
          </div>
          <div className="p-3 bg-white/5 rounded-lg">
            <div className="text-xs text-white/60">Correctness Rate</div>
            <div className="text-lg font-semibold text-green-400">
              {(metrics.correctnessRate * 100).toFixed(1)}%
            </div>
          </div>
        </div>

        {/* Confidence Distribution */}
        <div className="p-3 bg-white/5 rounded-lg">
          <h4 className="text-sm font-medium text-white mb-3">Confidence Distribution</h4>
          <div className="space-y-2">
            {metrics.confidenceDistribution.map(item => (
              <div key={item.range} className="flex items-center justify-between">
                <span className="text-xs text-white/80">{item.range}</span>
                <div className="flex items-center space-x-2">
                  <div className="w-16 bg-white/10 rounded-full h-2">
                    <div 
                      className="h-full bg-blue-400 rounded-full"
                      style={{ width: `${(item.count / metrics.totalCases) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-white/60 w-8">{item.count}</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Common Failure Modes */}
        <div className="p-3 bg-white/5 rounded-lg">
          <h4 className="text-sm font-medium text-white mb-3">Common Failure Modes</h4>
          <div className="space-y-2">
            {metrics.commonFailureModes.map(mode => (
              <div key={mode.mode} className="flex items-center justify-between">
                <span className="text-xs text-white/80">{mode.mode}</span>
                <div className="flex items-center space-x-2">
                  <span className="text-xs text-white/60">{mode.frequency}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                    mode.trend === 'increasing' ? 'bg-red-500/20 text-red-300' :
                    mode.trend === 'decreasing' ? 'bg-green-500/20 text-green-300' :
                    'bg-gray-500/20 text-gray-300'
                  }`}>
                    {mode.trend === 'increasing' ? '↗' : mode.trend === 'decreasing' ? '↘' : '→'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-white/5">
      {/* Header */}
      <div className="p-4 border-b border-white/10">
        <h2 className="text-lg font-semibold text-white mb-3">Domain Context</h2>
        
        {/* Domain Info */}
        <div className="text-sm text-white/60 mb-3">
          Domain: <span className="text-white/80 font-medium">{selectedCase.domain}</span>
        </div>
        
        {/* Tab Navigation */}
        <div className="flex space-x-1 bg-white/10 rounded-lg p-1">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 py-2 px-3 rounded-md text-xs font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-white/20 text-white shadow-sm'
                  : 'text-white/60 hover:text-white hover:bg-white/10'
              }`}
            >
              <span className="mr-1">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.2 }}
          >
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="w-6 h-6 border-2 border-white/20 border-t-white/60 rounded-full animate-spin" />
              </div>
            ) : (
              <>
                {activeTab === 'policies' && renderPolicies()}
                {activeTab === 'similar' && renderSimilarCases()}
                {activeTab === 'metrics' && renderMetrics()}
              </>
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  )
}