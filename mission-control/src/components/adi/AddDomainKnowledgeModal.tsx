/**
 * Add Domain Knowledge Modal - Interface for adding domain knowledge
 * 
 * This modal allows domain experts to:
 * - Add knowledge in YAML and text formats
 * - Validate knowledge before storage
 * - Trigger immediate re-scoring of similar cases
 * - Track knowledge impact and analytics
 * 
 * Requirements: 4.4, 4.5
 */

import React, { useState } from 'react'
import { motion } from 'framer-motion'
import type { DomainKnowledge } from '@/types/adi'
import '@/styles/glass-background.css'

interface AddDomainKnowledgeModalProps {
  onAdd: (knowledge: DomainKnowledge) => void
  onClose: () => void
}

type KnowledgeFormat = 'yaml' | 'text' | 'json'
type KnowledgeType = 'policy' | 'rule' | 'example' | 'context'

export const AddDomainKnowledgeModal: React.FC<AddDomainKnowledgeModalProps> = ({
  onAdd,
  onClose
}) => {
  const [domain, setDomain] = useState('')
  const [type, setType] = useState<KnowledgeType>('policy')
  const [format, setFormat] = useState<KnowledgeFormat>('yaml')
  const [content, setContent] = useState('')
  const [tags, setTags] = useState('')
  const [validationError, setValidationError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const knowledgeTypes = [
    { id: 'policy' as const, label: 'Policy', icon: '📋', description: 'Business rules and policies' },
    { id: 'rule' as const, label: 'Rule', icon: '⚖️', description: 'Logical rules and constraints' },
    { id: 'example' as const, label: 'Example', icon: '💡', description: 'Example cases and patterns' },
    { id: 'context' as const, label: 'Context', icon: '🔍', description: 'Background information' }
  ]

  const formats = [
    { id: 'yaml' as const, label: 'YAML', icon: '📄' },
    { id: 'text' as const, label: 'Text', icon: '📝' },
    { id: 'json' as const, label: 'JSON', icon: '🔧' }
  ]

  const validateContent = () => {
    setValidationError(null)

    if (!domain.trim()) {
      setValidationError('Domain is required')
      return false
    }

    if (!content.trim()) {
      setValidationError('Content is required')
      return false
    }

    // Format-specific validation
    if (format === 'yaml') {
      try {
        // Basic YAML validation (would use a proper YAML parser in production)
        if (!content.includes(':')) {
          setValidationError('Invalid YAML format - missing key-value pairs')
          return false
        }
      } catch (error) {
        setValidationError('Invalid YAML format')
        return false
      }
    }

    if (format === 'json') {
      try {
        JSON.parse(content)
      } catch (error) {
        setValidationError('Invalid JSON format')
        return false
      }
    }

    return true
  }

  const handleSubmit = async () => {
    if (!validateContent()) return

    setSubmitting(true)
    try {
      const knowledge: DomainKnowledge = {
        domain: domain.trim(),
        type,
        format,
        content: content.trim(),
        tags: tags.split(',').map(t => t.trim()).filter(Boolean),
        timestamp: new Date().toISOString()
      }

      await onAdd(knowledge)
    } catch (error) {
      console.error('Failed to add domain knowledge:', error)
      setValidationError('Failed to add knowledge. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const getPlaceholderContent = () => {
    switch (format) {
      case 'yaml':
        return `# Example policy
name: "Data Retention Policy"
rules:
  - condition: "data_type == 'personal'"
    retention_days: 365
    action: "archive_and_anonymize"
  - condition: "data_type == 'system_logs'"
    retention_days: 90
    action: "delete"`

      case 'json':
        return `{
  "name": "Data Retention Policy",
  "rules": [
    {
      "condition": "data_type == 'personal'",
      "retention_days": 365,
      "action": "archive_and_anonymize"
    }
  ]
}`

      default:
        return `Describe the domain knowledge in natural language.

For example:
- Business rules and constraints
- Decision-making guidelines
- Context and background information
- Examples of correct behavior`
    }
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
        className="glass-effect rounded-xl border border-white/20 max-w-4xl w-full max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-white/10">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-white">Add Domain Knowledge</h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-white/10 rounded-lg text-white/60 hover:text-white transition-colors"
            >
              ✕
            </button>
          </div>
          <p className="text-white/60 text-sm mt-2">
            Add knowledge that will improve AI decision-making in this domain
          </p>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[70vh]">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left Column - Configuration */}
            <div className="space-y-4">
              {/* Domain */}
              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  Domain
                </label>
                <input
                  type="text"
                  value={domain}
                  onChange={(e) => setDomain(e.target.value)}
                  placeholder="e.g., data-privacy, security, compliance"
                  className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:border-blue-400"
                />
              </div>

              {/* Knowledge Type */}
              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  Knowledge Type
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {knowledgeTypes.map(knowledgeType => (
                    <button
                      key={knowledgeType.id}
                      onClick={() => setType(knowledgeType.id)}
                      className={`p-3 rounded-lg border text-left transition-all ${
                        type === knowledgeType.id
                          ? 'border-blue-400/50 bg-blue-500/20'
                          : 'border-white/10 bg-white/5 hover:bg-white/10'
                      }`}
                    >
                      <div className="flex items-center space-x-2 mb-1">
                        <span>{knowledgeType.icon}</span>
                        <span className="text-sm font-medium text-white">{knowledgeType.label}</span>
                      </div>
                      <p className="text-xs text-white/60">{knowledgeType.description}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* Format */}
              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  Format
                </label>
                <div className="flex space-x-2">
                  {formats.map(formatOption => (
                    <button
                      key={formatOption.id}
                      onClick={() => setFormat(formatOption.id)}
                      className={`flex-1 py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                        format === formatOption.id
                          ? 'bg-white/20 text-white border border-white/30'
                          : 'bg-white/10 text-white/60 hover:text-white hover:bg-white/15'
                      }`}
                    >
                      <span className="mr-1">{formatOption.icon}</span>
                      {formatOption.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tags */}
              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  Tags (Optional)
                </label>
                <input
                  type="text"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  placeholder="tag1, tag2, tag3"
                  className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:border-blue-400"
                />
                <p className="text-xs text-white/60 mt-1">Separate tags with commas</p>
              </div>
            </div>

            {/* Right Column - Content */}
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-white mb-2">
                  Content
                </label>
                <textarea
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder={getPlaceholderContent()}
                  className="w-full h-80 px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:border-blue-400 font-mono text-sm resize-none"
                />
              </div>

              {/* Validation Error */}
              {validationError && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="p-3 bg-red-500/20 border border-red-400/50 rounded-lg"
                >
                  <div className="flex items-center space-x-2">
                    <span className="text-red-400">⚠️</span>
                    <span className="text-red-300 text-sm">{validationError}</span>
                  </div>
                </motion.div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-white/10 flex justify-between items-center">
          <div className="text-sm text-white/60">
            Knowledge will be validated and similar cases will be re-scored
          </div>
          <div className="flex space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-white/60 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="px-4 py-2 bg-green-500 hover:bg-green-600 disabled:bg-white/10 disabled:text-white/30 text-white rounded-lg font-medium transition-colors"
            >
              {submitting ? (
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                  <span>Adding...</span>
                </div>
              ) : (
                'Add Knowledge'
              )}
            </button>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}