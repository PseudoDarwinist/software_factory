/**
 * ADI Field Review - Domain expert interface for reviewing AI decisions
 * 
 * This component provides a three-pane interface for domain experts to:
 * - Review AI decisions and reasoning (CaseContextPane)
 * - Examine raw decision log data (EvidencePane)  
 * - Access domain policies and similar cases (DomainContextPane)
 * - Provide correctness feedback and tag failure modes
 * - Add domain knowledge and execute evaluations
 * 
 * Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 12.1
 */

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { GlassBackground } from '@/components/core/GlassBackground'
import { CaseContextPane } from '@/components/adi/CaseContextPane'
import { EvidencePane } from '@/components/adi/EvidencePane'
import { DomainContextPane } from '@/components/adi/DomainContextPane'
import { TagFailureModeModal } from '@/components/adi/TagFailureModeModal'
import { AddDomainKnowledgeModal } from '@/components/adi/AddDomainKnowledgeModal'
import { CreateWorkIdeaModal } from '@/components/adi/CreateWorkIdeaModal'
import { EvalExecutionPanel } from '@/components/adi/EvalExecutionPanel'
import { adiApi } from '@/services/api/adiApi'
import type { DecisionCase, FailureMode, DomainKnowledge } from '@/types/adi'

interface ADIFieldReviewProps {
  onClose?: () => void
}

export const ADIFieldReview: React.FC<ADIFieldReviewProps> = ({ onClose }) => {
  const [selectedCase, setSelectedCase] = useState<DecisionCase | null>(null)
  const [cases, setCases] = useState<DecisionCase[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Modal states
  const [showTagFailureModal, setShowTagFailureModal] = useState(false)
  const [showAddKnowledgeModal, setShowAddKnowledgeModal] = useState(false)
  const [showCreateWorkModal, setShowCreateWorkModal] = useState(false)
  const [showEvalPanel, setShowEvalPanel] = useState(false)

  // Load initial data
  useEffect(() => {
    loadCases()
  }, [])

  const loadCases = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await adiApi.getDecisionCases()
      setCases(data)
      if (data.length > 0) {
        setSelectedCase(data[0])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load cases')
    } finally {
      setLoading(false)
    }
  }

  const handleCorrectnessToggle = async (caseId: string, isCorrect: boolean) => {
    try {
      await adiApi.updateCaseCorrectness(caseId, isCorrect)
      // Update local state
      setCases(prev => prev.map(c => 
        c.id === caseId ? { ...c, isCorrect } : c
      ))
      if (selectedCase?.id === caseId) {
        setSelectedCase(prev => prev ? { ...prev, isCorrect } : null)
      }
    } catch (err) {
      console.error('Failed to update correctness:', err)
    }
  }

  const handleFailureModeTag = async (caseId: string, failureMode: FailureMode) => {
    try {
      await adiApi.tagFailureMode(caseId, failureMode)
      // Refresh case data
      loadCases()
      setShowTagFailureModal(false)
    } catch (err) {
      console.error('Failed to tag failure mode:', err)
    }
  }

  const handleAddDomainKnowledge = async (knowledge: DomainKnowledge) => {
    try {
      await adiApi.addDomainKnowledge(knowledge)
      // Trigger re-scoring of similar cases
      await adiApi.rescoreSimilarCases(knowledge.domain)
      setShowAddKnowledgeModal(false)
      // Refresh data
      loadCases()
    } catch (err) {
      console.error('Failed to add domain knowledge:', err)
    }
  }

  const handleCreateWorkIdea = async (insight: string, context: any) => {
    try {
      await adiApi.createWorkIdea(insight, context)
      setShowCreateWorkModal(false)
    } catch (err) {
      console.error('Failed to create work idea:', err)
    }
  }

  if (loading) {
    return (
      <GlassBackground className="h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-white/20 border-t-white/60 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-white/60">Loading ADI Field Review...</p>
        </div>
      </GlassBackground>
    )
  }

  if (error) {
    return (
      <GlassBackground className="h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-400 mb-4">⚠️ Error</div>
          <p className="text-white/60">{error}</p>
          <button 
            onClick={loadCases}
            className="mt-4 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-white transition-colors"
          >
            Retry
          </button>
        </div>
      </GlassBackground>
    )
  }

  return (
    <GlassBackground className="h-screen overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/10 backdrop-blur-md">
        <div className="flex items-center space-x-4">
          <img src="./ADI.png" alt="ADI" className="w-8 h-8" />
          <h1 className="text-xl font-semibold text-white">ADI Field Review</h1>
          <div className="text-sm text-white/60">
            {cases.length} cases • {selectedCase ? `Case ${selectedCase.id}` : 'No selection'}
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowEvalPanel(true)}
            className="px-3 py-1.5 bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 rounded-lg text-sm transition-colors"
          >
            Run Evaluation
          </button>
          <button
            onClick={() => setShowAddKnowledgeModal(true)}
            className="px-3 py-1.5 bg-green-500/20 hover:bg-green-500/30 text-green-300 rounded-lg text-sm transition-colors"
          >
            Add Knowledge
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/10 rounded-lg text-white/60 hover:text-white transition-colors"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Three-pane layout */}
      <div className="flex h-[calc(100vh-73px)]">
        {/* Left: Case Context Pane */}
        <div className="w-1/3 border-r border-white/10">
          <CaseContextPane
            cases={cases}
            selectedCase={selectedCase}
            onCaseSelect={setSelectedCase}
            onCorrectnessToggle={handleCorrectnessToggle}
            onTagFailureMode={() => setShowTagFailureModal(true)}
            onCreateWorkIdea={() => setShowCreateWorkModal(true)}
          />
        </div>

        {/* Center: Evidence Pane */}
        <div className="w-1/3 border-r border-white/10">
          <EvidencePane
            selectedCase={selectedCase}
          />
        </div>

        {/* Right: Domain Context Pane */}
        <div className="w-1/3">
          <DomainContextPane
            selectedCase={selectedCase}
          />
        </div>
      </div>

      {/* Modals */}
      <AnimatePresence>
        {showTagFailureModal && selectedCase && (
          <TagFailureModeModal
            caseId={selectedCase.id}
            onTag={handleFailureModeTag}
            onClose={() => setShowTagFailureModal(false)}
          />
        )}

        {showAddKnowledgeModal && (
          <AddDomainKnowledgeModal
            onAdd={handleAddDomainKnowledge}
            onClose={() => setShowAddKnowledgeModal(false)}
          />
        )}

        {showCreateWorkModal && selectedCase && (
          <CreateWorkIdeaModal
            caseContext={selectedCase}
            onCreate={handleCreateWorkIdea}
            onClose={() => setShowCreateWorkModal(false)}
          />
        )}

        {showEvalPanel && (
          <EvalExecutionPanel
            onClose={() => setShowEvalPanel(false)}
          />
        )}
      </AnimatePresence>
    </GlassBackground>
  )
}