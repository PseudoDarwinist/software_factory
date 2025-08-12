/**
 * Case Context Pane - Shows AI decision and reasoning
 * 
 * This component displays:
 * - List of decision cases
 * - Selected case details with AI decision and reasoning
 * - Correctness toggle controls
 * - Action buttons for tagging and work item creation
 * 
 * Requirements: 4.1
 */

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import type { DecisionCase } from '@/types/adi'

interface CaseContextPaneProps {
  cases: DecisionCase[]
  selectedCase: DecisionCase | null
  onCaseSelect: (decisionCase: DecisionCase) => void
  onCorrectnessToggle: (caseId: string, isCorrect: boolean) => void
  onTagFailureMode: () => void
  onCreateWorkIdea: () => void
}

export const CaseContextPane: React.FC<CaseContextPaneProps> = ({
  cases,
  selectedCase,
  onCaseSelect,
  onCorrectnessToggle,
  onTagFailureMode,
  onCreateWorkIdea
}) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [domainFilter, setDomainFilter] = useState<string>('')

  // Get unique domains for filtering
  const domains = Array.from(new Set(cases.map(c => c.domain)))

  // Filter cases based on search and domain
  const filteredCases = cases.filter(decisionCase => {
    const matchesSearch = decisionCase.decision.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         decisionCase.reasoning.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesDomain = !domainFilter || decisionCase.domain === domainFilter
    return matchesSearch && matchesDomain
  })

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-400'
    if (confidence >= 0.6) return 'text-yellow-400'
    return 'text-red-400'
  }

  const getCorrectnessIcon = (isCorrect?: boolean) => {
    if (isCorrect === true) return '✅'
    if (isCorrect === false) return '❌'
    return '❓'
  }

  return (
    <div className="h-full flex flex-col bg-white/5">
      {/* Header */}
      <div className="p-4 border-b border-white/10">
        <h2 className="text-lg font-semibold text-white mb-3">Case Context</h2>
        
        {/* Search and filters */}
        <div className="space-y-2">
          <input
            type="text"
            placeholder="Search decisions..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:border-blue-400"
          />
          
          <select
            value={domainFilter}
            onChange={(e) => setDomainFilter(e.target.value)}
            className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white focus:outline-none focus:border-blue-400"
          >
            <option value="">All Domains</option>
            {domains.map(domain => (
              <option key={domain} value={domain}>{domain}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Case List */}
      <div className="flex-1 overflow-y-auto">
        <div className="p-2 space-y-2">
          {filteredCases.map(decisionCase => (
            <motion.div
              key={decisionCase.id}
              onClick={() => onCaseSelect(decisionCase)}
              className={`p-3 rounded-lg cursor-pointer transition-all ${
                selectedCase?.id === decisionCase.id
                  ? 'bg-blue-500/20 border border-blue-400/50'
                  : 'bg-white/5 hover:bg-white/10 border border-transparent'
              }`}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  <span className="text-xs text-white/60">{decisionCase.domain}</span>
                  <span className="text-lg">{getCorrectnessIcon(decisionCase.isCorrect)}</span>
                </div>
                <div className={`text-xs font-mono ${getConfidenceColor(decisionCase.confidence)}`}>
                  {(decisionCase.confidence * 100).toFixed(1)}%
                </div>
              </div>
              
              <div className="text-sm text-white font-medium mb-1 line-clamp-2">
                {decisionCase.decision}
              </div>
              
              <div className="text-xs text-white/60 line-clamp-2">
                {decisionCase.reasoning}
              </div>
              
              <div className="text-xs text-white/40 mt-2">
                {new Date(decisionCase.timestamp).toLocaleString()}
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Selected Case Details */}
      <AnimatePresence>
        {selectedCase && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="border-t border-white/10 bg-white/5"
          >
            <div className="p-4">
              <h3 className="text-sm font-semibold text-white mb-3">Decision Details</h3>
              
              {/* Decision */}
              <div className="mb-3">
                <div className="text-xs text-white/60 mb-1">Decision</div>
                <div className="text-sm text-white">{selectedCase.decision}</div>
              </div>
              
              {/* Reasoning */}
              <div className="mb-3">
                <div className="text-xs text-white/60 mb-1">Reasoning</div>
                <div className="text-sm text-white/80 max-h-20 overflow-y-auto">
                  {selectedCase.reasoning}
                </div>
              </div>
              
              {/* Confidence */}
              <div className="mb-4">
                <div className="text-xs text-white/60 mb-1">Confidence</div>
                <div className="flex items-center space-x-2">
                  <div className="flex-1 bg-white/10 rounded-full h-2">
                    <div 
                      className="h-full bg-gradient-to-r from-red-500 via-yellow-500 to-green-500 rounded-full"
                      style={{ width: `${selectedCase.confidence * 100}%` }}
                    />
                  </div>
                  <span className={`text-xs font-mono ${getConfidenceColor(selectedCase.confidence)}`}>
                    {(selectedCase.confidence * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
              
              {/* Correctness Toggle */}
              <div className="mb-4">
                <div className="text-xs text-white/60 mb-2">Correctness Assessment</div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => onCorrectnessToggle(selectedCase.id, true)}
                    className={`flex-1 py-2 px-3 rounded-lg text-xs font-medium transition-colors ${
                      selectedCase.isCorrect === true
                        ? 'bg-green-500/30 text-green-300 border border-green-400/50'
                        : 'bg-white/10 text-white/60 hover:bg-green-500/20 hover:text-green-300'
                    }`}
                  >
                    ✅ Correct
                  </button>
                  <button
                    onClick={() => onCorrectnessToggle(selectedCase.id, false)}
                    className={`flex-1 py-2 px-3 rounded-lg text-xs font-medium transition-colors ${
                      selectedCase.isCorrect === false
                        ? 'bg-red-500/30 text-red-300 border border-red-400/50'
                        : 'bg-white/10 text-white/60 hover:bg-red-500/20 hover:text-red-300'
                    }`}
                  >
                    ❌ Incorrect
                  </button>
                </div>
              </div>
              
              {/* Action Buttons */}
              <div className="flex space-x-2">
                <button
                  onClick={onTagFailureMode}
                  disabled={selectedCase.isCorrect !== false}
                  className="flex-1 py-2 px-3 bg-orange-500/20 hover:bg-orange-500/30 disabled:bg-white/5 disabled:text-white/30 text-orange-300 rounded-lg text-xs font-medium transition-colors"
                >
                  🏷️ Tag Failure
                </button>
                <button
                  onClick={onCreateWorkIdea}
                  className="flex-1 py-2 px-3 bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 rounded-lg text-xs font-medium transition-colors"
                >
                  💡 Create Work
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}