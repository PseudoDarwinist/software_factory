/**
 * Create Work Idea Modal - Interface for converting insights to work items
 * 
 * This modal allows domain experts to:
 * - Convert case insights into work items for the Think stage
 * - Integrate with existing Think stage workflow
 * - Track work item status and updates
 * - Create bidirectional linking between insights and work items
 * 
 * Requirements: 4.6, 12.1
 */

import React, { useState } from 'react'
import { motion } from 'framer-motion'
import type { DecisionCase } from '@/types/adi'
import '@/styles/glass-background.css'

interface CreateWorkIdeaModalProps {
  caseContext: DecisionCase
  onCreate: (insight: string, context: any) => void
  onClose: () => void
}

type Priority = 'low' | 'medium' | 'high'

export const CreateWorkIdeaModal: React.FC<CreateWorkIdeaModalProps> = ({
  caseContext,
  onCreate,
  onClose
}) => {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState<Priority>('medium')
  const [insights, setInsights] = useState<string[]>([''])
  const [submitting, setSubmitting] = useState(false)

  const priorityOptions = [
    { id: 'low' as const, label: 'Low', color: 'text-green-400 bg-green-500/20', icon: '🟢' },
    { id: 'medium' as const, label: 'Medium', color: 'text-yellow-400 bg-yellow-500/20', icon: '🟡' },
    { id: 'high' as const, label: 'High', color: 'text-red-400 bg-red-500/20', icon: '🔴' }
  ]

  const addInsight = () => {
    setInsights([...insights, ''])
  }

  const updateInsight = (index: number, value: string) => {
    const newInsights = [...insights]
    newInsights[index] = value
    setInsights(newInsights)
  }

  const removeInsight = (index: number) => {
    if (insights.length > 1) {
      setInsights(insights.filter((_, i) => i !== index))
    }
  }

  const handleSubmit = async () => {
    if (!title.trim() || !description.trim()) return

    setSubmitting(true)
    try {
      const workContext = {
        sourceCase: caseContext.id,
        domain: caseContext.domain,
        decision: caseContext.decision,
        reasoning: caseContext.reasoning,
        confidence: caseContext.confidence,
        isCorrect: caseContext.isCorrect,
        priority,
        insights: insights.filter(i => i.trim()),
        timestamp: new Date().toISOString()
      }

      const insight = `${title}\n\n${description}\n\nInsights:\n${insights.filter(i => i.trim()).map(i => `- ${i}`).join('\n')}`
      
      await onCreate(insight, workContext)
    } catch (error) {
      console.error('Failed to create work idea:', error)
    } finally {
      setSubmitting(false)
    }
  }

  // Generate suggested title based on case context
  const suggestedTitle = `Improve ${caseContext.domain} decision accuracy`

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
        className="glass-effect rounded-xl border border-white/20 max-w-3xl w-full max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-white/10">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-white">Create Work Idea</h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/10 rounded-lg text-white/60 hover:text-white transition-colors"
            >
              ✕
            </button>
          </div>
          <p className="text-white/60 text-sm mt-2">
            Convert this case insight into a work item for the Think stage
          </p>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[70vh]">
          <div className="space-y-6">
            {/* Case Context Summary */}
            <div className="p-4 bg-white/5 rounded-lg border border-white/10">
              <h3 className="text-sm font-medium text-white mb-2">Source Case Context</h3>
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div>
                  <span className="text-white/60">Domain:</span>
                  <span className="text-white ml-2">{caseContext.domain}</span>
                </div>
                <div>
                  <span className="text-white/60">Correctness:</span>
                  <span className="text-white ml-2">
                    {caseContext.isCorrect === true ? '✅ Correct' : 
                     caseContext.isCorrect === false ? '❌ Incorrect' : '❓ Unknown'}
                  </span>
                </div>
                <div className="col-span-2">
                  <span className="text-white/60">Decision:</span>
                  <p className="text-white/80 mt-1 text-sm">{caseContext.decision}</p>
                </div>
              </div>
            </div>

            {/* Work Idea Details */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Main Details */}
              <div className="lg:col-span-2 space-y-4">
                {/* Title */}
                <div>
                  <label className="block text-sm font-medium text-white mb-2">
                    Work Idea Title
                  </label>
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder={suggestedTitle}
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:border-blue-400"
                  />
                  {!title && (
                    <button
                      onClick={() => setTitle(suggestedTitle)}
                      className="text-xs text-blue-400 hover:text-blue-300 mt-1"
                    >
                      Use suggested title
                    </button>
                  )}
                </div>

                {/* Description */}
                <div>
                  <label className="block text-sm font-medium text-white mb-2">
                    Description
                  </label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Describe the work needed to address the insights from this case..."
                    className="w-full h-32 px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:border-blue-400 resize-none"
                  />
                </div>

                {/* Insights */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="block text-sm font-medium text-white">
                      Key Insights
                    </label>
                    <button
                      onClick={addInsight}
                      className="text-xs text-blue-400 hover:text-blue-300"
                    >
                      + Add Insight
                    </button>
                  </div>
                  <div className="space-y-2">
                    {insights.map((insight, index) => (
                      <div key={index} className="flex items-center space-x-2">
                        <input
                          type="text"
                          value={insight}
                          onChange={(e) => updateInsight(index, e.target.value)}
                          placeholder={`Insight ${index + 1}...`}
                          className="flex-1 px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:border-blue-400"
                        />
                        {insights.length > 1 && (
                          <button
                            onClick={() => removeInsight(index)}
                            className="p-2 text-white/60 hover:text-red-400 transition-colors"
                          >
                            ✕
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Priority & Settings */}
              <div className="space-y-4">
                {/* Priority */}
                <div>
                  <label className="block text-sm font-medium text-white mb-2">
                    Priority
                  </label>
                  <div className="space-y-2">
                    {priorityOptions.map(option => (
                      <button
                        key={option.id}
                        onClick={() => setPriority(option.id)}
                        className={`w-full p-3 rounded-lg border text-left transition-all ${
                          priority === option.id
                            ? 'border-blue-400/50 bg-blue-500/20'
                            : 'border-white/10 bg-white/5 hover:bg-white/10'
                        }`}
                      >
                        <div className="flex items-center space-x-2">
                          <span>{option.icon}</span>
                          <span className="text-sm font-medium text-white">{option.label}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Integration Info */}
                <div className="p-3 bg-blue-500/10 border border-blue-400/20 rounded-lg">
                  <h4 className="text-sm font-medium text-blue-300 mb-2">Think Stage Integration</h4>
                  <p className="text-xs text-blue-200/80">
                    This work idea will be added to the Think stage and linked to this case for tracking.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-white/10 flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-white/60 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!title.trim() || !description.trim() || submitting}
            className="px-4 py-2 bg-purple-500 hover:bg-purple-600 disabled:bg-white/10 disabled:text-white/30 text-white rounded-lg font-medium transition-colors"
          >
            {submitting ? (
              <div className="flex items-center space-x-2">
                <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                <span>Creating...</span>
              </div>
            ) : (
              'Create Work Idea'
            )}
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}