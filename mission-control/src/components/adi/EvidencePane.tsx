/**
 * Evidence Pane - Displays raw decision log data
 * 
 * This component shows:
 * - Raw request/response data from decision logs
 * - Metadata about the AI model and execution
 * - Context information used in the decision
 * - Formatted JSON/YAML display with syntax highlighting
 * 
 * Requirements: 4.1
 */

import React, { useState } from 'react'
import { motion } from 'framer-motion'
import type { DecisionCase } from '@/types/adi'

interface EvidencePaneProps {
  selectedCase: DecisionCase | null
}

type EvidenceTab = 'request' | 'response' | 'context' | 'metadata'

export const EvidencePane: React.FC<EvidencePaneProps> = ({ selectedCase }) => {
  const [activeTab, setActiveTab] = useState<EvidenceTab>('request')

  if (!selectedCase) {
    return (
      <div className="h-full flex items-center justify-center bg-white/5">
        <div className="text-center text-white/60">
          <div className="text-4xl mb-4">📋</div>
          <p>Select a case to view evidence</p>
        </div>
      </div>
    )
  }

  const tabs: Array<{ id: EvidenceTab; label: string; icon: string }> = [
    { id: 'request', label: 'Request', icon: '📤' },
    { id: 'response', label: 'Response', icon: '📥' },
    { id: 'context', label: 'Context', icon: '🔍' },
    { id: 'metadata', label: 'Metadata', icon: '⚙️' }
  ]

  const formatData = (data: any): string => {
    if (typeof data === 'string') return data
    return JSON.stringify(data, null, 2)
  }

  const getTabContent = () => {
    const { rawData } = selectedCase
    
    switch (activeTab) {
      case 'request':
        return formatData(rawData.request)
      case 'response':
        return formatData(rawData.response)
      case 'context':
        return formatData(rawData.context)
      case 'metadata':
        return formatData(rawData.metadata)
      default:
        return ''
    }
  }

  const getLineCount = (content: string): number => {
    return content.split('\n').length
  }

  return (
    <div className="h-full flex flex-col bg-white/5">
      {/* Header */}
      <div className="p-4 border-b border-white/10">
        <h2 className="text-lg font-semibold text-white mb-3">Evidence</h2>
        
        {/* Case Info */}
        <div className="text-sm text-white/60 mb-3">
          Case ID: <span className="font-mono text-white/80">{selectedCase.id}</span>
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
      <div className="flex-1 overflow-hidden">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.2 }}
          className="h-full"
        >
          {/* Content Header */}
          <div className="px-4 py-2 border-b border-white/10 bg-white/5">
            <div className="flex items-center justify-between">
              <div className="text-sm font-medium text-white">
                {tabs.find(t => t.id === activeTab)?.label} Data
              </div>
              <div className="text-xs text-white/60">
                {getLineCount(getTabContent())} lines
              </div>
            </div>
          </div>

          {/* JSON/Data Display */}
          <div className="h-[calc(100%-49px)] overflow-auto">
            <pre className="p-4 text-xs font-mono text-white/80 leading-relaxed whitespace-pre-wrap">
              <code className="language-json">
                {getTabContent()}
              </code>
            </pre>
          </div>
        </motion.div>
      </div>

      {/* Footer with metadata summary */}
      <div className="p-3 border-t border-white/10 bg-white/5">
        <div className="grid grid-cols-2 gap-4 text-xs">
          <div>
            <div className="text-white/60">Model</div>
            <div className="text-white font-mono">{selectedCase.rawData.metadata.model}</div>
          </div>
          <div>
            <div className="text-white/60">Version</div>
            <div className="text-white font-mono">{selectedCase.rawData.metadata.version}</div>
          </div>
          <div>
            <div className="text-white/60">Latency</div>
            <div className="text-white font-mono">{selectedCase.rawData.metadata.latency}ms</div>
          </div>
          <div>
            <div className="text-white/60">Tokens</div>
            <div className="text-white font-mono">{selectedCase.rawData.metadata.tokens}</div>
          </div>
        </div>
      </div>
    </div>
  )
}