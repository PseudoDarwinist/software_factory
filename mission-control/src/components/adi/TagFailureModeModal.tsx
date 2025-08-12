/**
 * Tag Failure Mode Modal - Interface for tagging failure modes
 * 
 * This modal allows domain experts to:
 * - Select failure modes from ontology dropdown
 * - Tag cases with specific failure modes
 * - Track failure mode frequency and analytics
 * 
 * Requirements: 4.2, 4.3
 */

import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { adiApi } from '@/services/api/adiApi'
import type { FailureMode } from '@/types/adi'
import '@/styles/glass-background.css'

interface TagFailureModeModalProps {
  caseId: string
  onTag: (caseId: string, failureMode: FailureMode) => void
  onClose: () => void
}

export const TagFailureModeModal: React.FC<TagFailureModeModalProps> = ({
  caseId,
  onTag,
  onClose
}) => {
  const [failureModes, setFailureModes] = useState<FailureMode[]>([])
  const [selectedMode, setSelectedMode] = useState<FailureMode | null>(null)
  const [customDescription, setCustomDescription] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    loadFailureModes()
  }, [])

  const loadFailureModes = async () => {
    try {
      const modes = await adiApi.getFailureModes()
      setFailureModes(modes)
    } catch (error) {
      console.error('Failed to load failure modes:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async () => {
    if (!selectedMode) return

    setSubmitting(true)
    try {
      const modeToTag = {
        ...selectedMode,
        description: customDescription || selectedMode.description
      }
      await onTag(caseId, modeToTag)
    } catch (error) {
      console.error('Failed to tag failure mode:', error)
    } finally {
      setSubmitting(false)
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-400 bg-red-500/20'
      case 'high': return 'text-orange-400 bg-orange-500/20'
      case 'medium': return 'text-yellow-400 bg-yellow-500/20'
      case 'low': return 'text-green-400 bg-green-500/20'
      default: return 'text-gray-400 bg-gray-500/20'
    }
  }

  const groupedModes = failureModes.reduce((acc, mode) => {
    if (!acc[mode.category]) {
      acc[mode.category] = []
    }
    acc[mode.category].push(mode)
    return acc
  }, {} as Record<string, FailureMode[]>)

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
        className="glass-effect rounded-xl border border-white/20 max-w-2xl w-full max-h-[80vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-white/10">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-white">Tag Failure Mode</h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/10 rounded-lg text-white/60 hover:text-white transition-colors"
            >
              ✕
            </button>
          </div>
          <p className="text-white/60 text-sm mt-2">
            Select a failure mode to tag this incorrect decision
          </p>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-6 h-6 border-2 border-white/20 border-t-white/60 rounded-full animate-spin" />
            </div>
          ) : (
            <div className="space-y-6">
              {/* Failure Mode Selection */}
              <div>
                <label className="block text-sm font-medium text-white mb-3">
                  Select Failure Mode
                </label>
                <div className="space-y-4">
                  {Object.entries(groupedModes).map(([category, modes]) => (
                    <div key={category}>
                      <h3 className="text-sm font-medium text-white/80 mb-2 uppercase tracking-wide">
                        {category}
                      </h3>
                      <div className="space-y-2">
                        {modes.map(mode => (
                          <motion.div
                            key={mode.id}
                            className={`p-3 rounded-lg border cursor-pointer transition-all ${
                              selectedMode?.id === mode.id
                                ? 'border-blue-400/50 bg-blue-500/20'
                                : 'border-white/10 bg-white/5 hover:bg-white/10'
                            }`}
                            onClick={() => setSelectedMode(mode)}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                          >
                            <div className="flex items-center justify-between mb-2">
                              <h4 className="text-sm font-medium text-white">{mode.name}</h4>
                              <div className="flex items-center space-x-2">
                                <span className={`text-xs px-2 py-1 rounded ${getSeverityColor(mode.severity)}`}>
                                  {mode.severity}
                                </span>
                                {mode.frequency && (
                                  <span className="text-xs text-white/60">
                                    {mode.frequency} cases
                                  </span>
                                )}
                              </div>
                            </div>
                            <p className="text-xs text-white/70">{mode.description}</p>
                          </motion.div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Custom Description */}
              {selectedMode && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="space-y-2"
                >
                  <label className="block text-sm font-medium text-white">
                    Additional Notes (Optional)
                  </label>
                  <textarea
                    value={customDescription}
                    onChange={(e) => setCustomDescription(e.target.value)}
                    placeholder="Add specific details about this failure..."
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:border-blue-400 resize-none"
                    rows={3}
                  />
                </motion.div>
              )}
            </div>
          )}
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
            disabled={!selectedMode || submitting}
            className="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-white/10 disabled:text-white/30 text-white rounded-lg font-medium transition-colors"
          >
            {submitting ? (
              <div className="flex items-center space-x-2">
                <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                <span>Tagging...</span>
              </div>
            ) : (
              'Tag Failure Mode'
            )}
          </button>
        </div>
      </motion.div>
    </motion.div>
  )
}