/**
 * DefineStage - The Define stage UI with Product Brief editor
 * 
 * This component creates the innovative Define stage experience where:
 * 1. Left side shows "Ideas in Definition" 
 * 2. Right side shows the Product Brief editor
 * 3. Progress bar tracks completion
 * 4. Smooth transitions and liquid glass aesthetics
 * 
 * When an idea is dragged from Think to Define:
 * - The center column morphs into "Ideas in Definition"
 * - The right panel becomes the Product Brief editor
 * - Progress bar appears showing completion percentage
 * - LLM pre-populates sections with intelligent starter content
 * 
 * This matches the Jony Ive on acid design philosophy - 
 * innovative, coherent, and seamlessly integrated.
 */

import React, { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { LiquidCard } from '@/components/core/LiquidCard'
import { tokens } from '@/styles/tokens'
import { missionControlApi } from '@/services/api/missionControlApi'
import type { FeedItem, SDLCStage } from '@/types'

interface DefineStageProps {
  feedItems: FeedItem[]
  selectedProject: string | null
  selectedFeedItem: string | null
  onFeedItemSelect: (feedItemId: string | null) => void
  onStageChange: (stage: SDLCStage) => void
  loading: boolean
  error: string | null
}

interface ProductBrief {
  id: string
  itemId: string
  projectId: string
  problemStatement: string
  successMetrics: string[]
  risks: string[]
  competitiveAnalysis: string
  userStories: UserStory[]
  progress: number
  status: 'draft' | 'frozen'
  createdAt: string
  updatedAt: string
}

interface UserStory {
  id: string
  title: string
  description: string
  acceptanceCriteria: string[]
  priority: 'high' | 'medium' | 'low'
}

export const DefineStage: React.FC<DefineStageProps> = ({
  feedItems,
  selectedProject,
  selectedFeedItem,
  onFeedItemSelect,
  onStageChange,
  loading,
  error,
}) => {
  const [ideasInDefinition, setIdeasInDefinition] = useState<FeedItem[]>([])
  const [currentBrief, setCurrentBrief] = useState<ProductBrief | null>(null)
  const [briefLoading, setBriefLoading] = useState(false)
  const [briefError, setBriefError] = useState<string | null>(null)

  // Filter ideas that are in definition stage
  useEffect(() => {
    const definitionItems = feedItems.filter(item => 
      item.kind === 'idea' && 
      item.metadata?.stage === 'define'
    )
    setIdeasInDefinition(definitionItems)
  }, [feedItems])

  // Load product brief when an item is selected
  useEffect(() => {
    if (selectedFeedItem) {
      loadProductBrief(selectedFeedItem)
    } else {
      setCurrentBrief(null)
    }
  }, [selectedFeedItem])

  const loadProductBrief = async (itemId: string) => {
    try {
      setBriefLoading(true)
      setBriefError(null)
      
      const briefId = `brief-${itemId}`
      const brief = await missionControlApi.getProductBrief(briefId)
      setCurrentBrief(brief)
    } catch (error) {
      setBriefError('Failed to load product brief')
      console.error('Error loading product brief:', error)
    } finally {
      setBriefLoading(false)
    }
  }

  const updateBrief = useCallback(async (updates: Partial<ProductBrief>) => {
    if (!currentBrief) return

    try {
      await missionControlApi.updateProductBrief(currentBrief.id, updates)
      setCurrentBrief(prev => prev ? { ...prev, ...updates } : null)
    } catch (error) {
      console.error('Error updating product brief:', error)
    }
  }, [currentBrief])

  const freezeBrief = useCallback(async () => {
    if (!currentBrief) return

    try {
      await missionControlApi.freezeProductBrief(currentBrief.id)
      setCurrentBrief(prev => prev ? { ...prev, status: 'frozen' } : null)
      
      // Transition to Plan stage
      onStageChange('plan')
    } catch (error) {
      console.error('Error freezing product brief:', error)
    }
  }, [currentBrief, onStageChange])

  const calculateProgress = useCallback((brief: ProductBrief) => {
    let completed = 0
    let total = 5 // 5 main sections
    
    if (brief.problemStatement.trim()) completed++
    if (brief.successMetrics.length > 0) completed++
    if (brief.risks.length > 0) completed++
    if (brief.competitiveAnalysis.trim()) completed++
    if (brief.userStories.length > 0) completed++
    
    return Math.round((completed / total) * 100)
  }, [])

  return (
    <div className="h-full flex">
      {/* Left Side - Ideas in Definition */}
      <motion.div
        initial={{ x: -300, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
        className="w-80 bg-black/20 backdrop-blur-md border-r border-white/10 flex flex-col"
      >
        <div className="p-4 border-b border-white/10">
          <h2 className="text-lg font-semibold text-white mb-2">Ideas in Definition</h2>
          <div className="text-xs text-white/60 bg-white/10 px-2 py-1 rounded-full inline-block">
            {ideasInDefinition.length} items
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {ideasInDefinition.map((item) => (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <LiquidCard
                variant="feed"
                severity="info"
                urgency="medium"
                onClick={() => onFeedItemSelect(item.id)}
                className={clsx(
                  'cursor-pointer transition-all',
                  selectedFeedItem === item.id && 'ring-2 ring-blue-500/50'
                )}
              >
                <div className="flex items-start space-x-3">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center">
                    <span className="text-blue-400 text-sm">📝</span>
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <h4 className="font-medium text-white text-sm leading-tight">
                      {item.title}
                    </h4>
                    <p className="text-xs text-white/70 mt-1 line-clamp-2">
                      {item.summary}
                    </p>
                    <div className="flex items-center justify-between mt-2">
                      <div className="text-xs text-white/50">
                        {item.actor}
                      </div>
                      <div className="text-xs text-blue-400 bg-blue-500/20 px-2 py-1 rounded-full">
                        In Definition
                      </div>
                    </div>
                  </div>
                </div>
              </LiquidCard>
            </motion.div>
          ))}

          {ideasInDefinition.length === 0 && (
            <div className="text-center py-8">
              <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-white/5 flex items-center justify-center">
                <span className="text-white/40 text-lg">📝</span>
              </div>
              <h3 className="text-sm font-medium text-white/80 mb-2">No ideas in definition</h3>
              <p className="text-xs text-white/60">
                Drag ideas from Think to start defining them
              </p>
            </div>
          )}
        </div>
      </motion.div>

      {/* Right Side - Product Brief Editor */}
      <motion.div
        initial={{ x: 300, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.5, ease: 'easeOut', delay: 0.1 }}
        className="flex-1 bg-black/10 backdrop-blur-sm flex flex-col"
      >
        {currentBrief && (
          <>
            {/* Progress Bar */}
            <div className="h-1 bg-white/10 relative">
              <motion.div
                className="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-500 to-green-500"
                initial={{ width: 0 }}
                animate={{ width: `${calculateProgress(currentBrief)}%` }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
              />
            </div>

            {/* Header */}
            <div className="p-6 border-b border-white/10">
              <div className="flex items-center justify-between">
                <div>
                  <h1 className="text-2xl font-bold text-white mb-2">Product Brief</h1>
                  <p className="text-white/70 text-sm">
                    {calculateProgress(currentBrief)}% complete
                  </p>
                </div>
                
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={freezeBrief}
                  disabled={calculateProgress(currentBrief) < 80}
                  className={clsx(
                    'px-6 py-2 rounded-lg font-medium transition-all',
                    calculateProgress(currentBrief) >= 80
                      ? 'bg-blue-600 hover:bg-blue-700 text-white'
                      : 'bg-white/10 text-white/50 cursor-not-allowed'
                  )}
                >
                  Freeze spec
                </motion.button>
              </div>
            </div>

            {/* Brief Content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-8">
              <ProductBriefEditor
                brief={currentBrief}
                onUpdate={updateBrief}
                loading={briefLoading}
                error={briefError}
              />
            </div>
          </>
        )}

        {!currentBrief && !briefLoading && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center text-white/60 p-8">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-white/5 flex items-center justify-center">
                <span className="text-white/40 text-2xl">📝</span>
              </div>
              <h3 className="text-lg font-medium mb-2">Select an idea to define</h3>
              <p className="text-sm">
                Choose an idea from the left to start creating its product brief
              </p>
            </div>
          </div>
        )}

        {briefLoading && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-white/10 flex items-center justify-center">
                <svg className="w-6 h-6 animate-spin text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </div>
              <p className="text-white/80">Loading product brief...</p>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  )
}

interface ProductBriefEditorProps {
  brief: ProductBrief
  onUpdate: (updates: Partial<ProductBrief>) => void
  loading: boolean
  error: string | null
}

const ProductBriefEditor: React.FC<ProductBriefEditorProps> = ({
  brief,
  onUpdate,
  loading,
  error,
}) => {
  const [localBrief, setLocalBrief] = useState(brief)

  useEffect(() => {
    setLocalBrief(brief)
  }, [brief])

  const handleFieldChange = (field: keyof ProductBrief, value: any) => {
    setLocalBrief(prev => ({ ...prev, [field]: value }))
    onUpdate({ [field]: value })
  }

  return (
    <div className="space-y-8">
      {/* Problem Statement */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="space-y-3"
      >
        <h3 className="text-lg font-semibold text-white">Problem Statement</h3>
        <textarea
          value={localBrief.problemStatement}
          onChange={(e) => handleFieldChange('problemStatement', e.target.value)}
          placeholder="Describe the user problem this feature will solve..."
          className="w-full h-24 bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none"
        />
      </motion.div>

      {/* Success Metrics */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="space-y-3"
      >
        <h3 className="text-lg font-semibold text-white">Success Metrics</h3>
        <div className="space-y-2">
          {localBrief.successMetrics.map((metric, index) => (
            <div key={index} className="flex items-center space-x-2">
              <input
                type="text"
                value={metric}
                onChange={(e) => {
                  const newMetrics = [...localBrief.successMetrics]
                  newMetrics[index] = e.target.value
                  handleFieldChange('successMetrics', newMetrics)
                }}
                placeholder="Define a success metric..."
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              />
              <button
                onClick={() => {
                  const newMetrics = localBrief.successMetrics.filter((_, i) => i !== index)
                  handleFieldChange('successMetrics', newMetrics)
                }}
                className="text-red-400 hover:text-red-300 p-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
          <button
            onClick={() => handleFieldChange('successMetrics', [...localBrief.successMetrics, ''])}
            className="text-blue-400 hover:text-blue-300 text-sm font-medium"
          >
            + Add metric
          </button>
        </div>
      </motion.div>

      {/* Risks */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="space-y-3"
      >
        <h3 className="text-lg font-semibold text-white">Risks</h3>
        <div className="space-y-2">
          {localBrief.risks.map((risk, index) => (
            <div key={index} className="flex items-center space-x-2">
              <input
                type="text"
                value={risk}
                onChange={(e) => {
                  const newRisks = [...localBrief.risks]
                  newRisks[index] = e.target.value
                  handleFieldChange('risks', newRisks)
                }}
                placeholder="Identify a potential risk..."
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
              />
              <button
                onClick={() => {
                  const newRisks = localBrief.risks.filter((_, i) => i !== index)
                  handleFieldChange('risks', newRisks)
                }}
                className="text-red-400 hover:text-red-300 p-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))}
          <button
            onClick={() => handleFieldChange('risks', [...localBrief.risks, ''])}
            className="text-blue-400 hover:text-blue-300 text-sm font-medium"
          >
            + Add risk
          </button>
        </div>
      </motion.div>

      {/* Competitive Analysis */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="space-y-3"
      >
        <h3 className="text-lg font-semibold text-white">Competitive Analysis</h3>
        <textarea
          value={localBrief.competitiveAnalysis}
          onChange={(e) => handleFieldChange('competitiveAnalysis', e.target.value)}
          placeholder="How do competitors handle this? What can we learn?"
          className="w-full h-32 bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder-white/50 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none"
        />
      </motion.div>
    </div>
  )
}

export default DefineStage