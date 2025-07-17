/**
 * ConversationColumn - Right panel showing contextual conversation and evidence
 * 
 * This component displays the "smart notebook" that always opens to the exact
 * page needed for the selected feed item. It includes:
 * - Timeline of events
 * - Code diffs and evidence
 * - Spec snippets and context
 * - AI suggestions and prompts
 * - Interactive prompt box for actions
 * 
 * Why this component exists:
 * - Provides all context needed for decision making
 * - Eliminates need to hunt through multiple tools
 * - Offers intelligent suggestions for next actions
 * - Maintains conversation flow with AI agents
 * 
 * For AI agents: This is where contextual information is displayed
 * and where users interact with AI suggestions and prompts.
 */

import React, { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { LiquidCard } from '@/components/core/LiquidCard'
import { tokens } from '@/styles/tokens'
import type { ConversationPayload, ConversationBlock, TimelineEvent } from '@/types'

interface ConversationColumnProps {
  conversation: ConversationPayload | null
  onPromptSubmit: (prompt: string) => void
  loading: boolean
  error: string | null
  onClose?: () => void
}

export const ConversationColumn: React.FC<ConversationColumnProps> = ({
  conversation,
  onPromptSubmit,
  loading,
  error,
  onClose,
}) => {
  const [prompt, setPrompt] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const promptRef = useRef<HTMLTextAreaElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-focus prompt when conversation loads
  useEffect(() => {
    if (conversation && promptRef.current) {
      promptRef.current.focus()
      setPrompt(conversation.suggestedPrompt || '')
    }
  }, [conversation])

  // Auto-scroll to bottom when new content appears
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [conversation])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt.trim() || isSubmitting) return

    setIsSubmitting(true)
    try {
      await onPromptSubmit(prompt)
      setPrompt('')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleSubmit(e)
    }
  }

  if (!conversation && !loading) {
    return null
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-white/10">
        <h2 className="text-lg font-semibold text-white">Context</h2>
        {onClose && (
          <button
            onClick={onClose}
            className="p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors"
            aria-label="Close conversation"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 flex flex-col min-h-0">
        {/* Conversation blocks */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
          {loading && (
            <div className="space-y-4">
              {[...Array(4)].map((_, i) => (
                <div
                  key={i}
                  className="h-20 bg-white/5 rounded-lg animate-pulse"
                  style={{ animationDelay: `${i * 0.2}s` }}
                />
              ))}
            </div>
          )}

          {error && (
            <div className="text-center py-8">
              <div className="text-red-400 text-sm mb-2">Failed to load conversation</div>
              <button
                onClick={() => window.location.reload()}
                className="text-xs text-white/60 hover:text-white/80"
              >
                Try again
              </button>
            </div>
          )}

          {conversation && (
            <AnimatePresence>
              {conversation.blocks.map((block, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <ConversationBlockRenderer block={block} />
                </motion.div>
              ))}
            </AnimatePresence>
          )}
        </div>

        {/* Prompt input */}
        {conversation && (
          <div className="border-t border-white/10 p-4">
            <form onSubmit={handleSubmit} className="space-y-3">
              <div className="relative">
                <textarea
                  ref={promptRef}
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type your response or command..."
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-white/50 focus:outline-none focus:border-white/20 focus:bg-white/10 resize-none transition-all"
                  rows={3}
                  disabled={isSubmitting}
                />
                
                {/* Command suggestions */}
                {prompt.startsWith('/') && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-black/80 backdrop-blur-sm rounded-lg border border-white/10 p-2 space-y-1 z-10">
                    {getCommandSuggestions(prompt).map((suggestion, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => setPrompt(suggestion.command)}
                        className="w-full text-left px-3 py-2 hover:bg-white/10 rounded text-sm transition-colors"
                      >
                        <div className="flex items-center space-x-2">
                          <span className="text-green-400">{suggestion.command}</span>
                          <span className="text-white/60">-</span>
                          <span className="text-white/80">{suggestion.description}</span>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between">
                <div className="text-xs text-white/50">
                  ⌘ + Enter to send
                </div>
                
                <button
                  type="submit"
                  disabled={!prompt.trim() || isSubmitting}
                  className={clsx(
                    'flex items-center space-x-2 px-4 py-2 rounded-lg font-medium text-sm transition-all',
                    prompt.trim() && !isSubmitting
                      ? 'bg-green-600 hover:bg-green-500 text-white'
                      : 'bg-white/10 text-white/50 cursor-not-allowed'
                  )}
                >
                  {isSubmitting ? (
                    <>
                      <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      <span>Sending...</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                      </svg>
                      <span>Send</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  )
}

interface ConversationBlockRendererProps {
  block: ConversationBlock
}

const ConversationBlockRenderer: React.FC<ConversationBlockRendererProps> = ({ block }) => {
  switch (block.type) {
    case 'timeline':
      return <TimelineBlock events={block.events} />
    case 'code_diff':
      return <CodeDiffBlock {...block} />
    case 'image_compare':
      return <ImageCompareBlock {...block} />
    case 'spec_snippet':
      return <SpecSnippetBlock {...block} />
    case 'log_excerpt':
      return <LogExcerptBlock {...block} />
    case 'metric':
      return <MetricBlock {...block} />
    case 'llm_suggestion':
      return <LLMSuggestionBlock {...block} />
    case 'file_list':
      return <FileListBlock {...block} />
    case 'test_results':
      return <TestResultsBlock {...block} />
    default:
      return <div className="text-white/60 text-sm">Unknown block type</div>
  }
}

const TimelineBlock: React.FC<{ events: TimelineEvent[] }> = ({ events }) => (
  <LiquidCard variant="conversation" className="space-y-3">
    <h3 className="text-sm font-medium text-white/80 mb-3">Timeline</h3>
    <div className="space-y-2">
      {events.map((event, i) => (
        <div key={event.id || i} className="flex items-start space-x-3">
          <div className="w-2 h-2 bg-white/40 rounded-full mt-2 flex-shrink-0" />
          <div className="flex-1">
            <div className="flex items-center space-x-2 text-xs text-white/60 mb-1">
              <span>{new Date(event.time).toLocaleTimeString()}</span>
              <span>•</span>
              <span className="font-medium">{event.actor}</span>
            </div>
            <p className="text-sm text-white/90">{event.message}</p>
          </div>
        </div>
      ))}
    </div>
  </LiquidCard>
)

const CodeDiffBlock: React.FC<{ before: string; after: string; language: string; filePath: string }> = ({
  before,
  after,
  language,
  filePath,
}) => (
  <LiquidCard variant="conversation">
    <h3 className="text-sm font-medium text-white/80 mb-3">Code Changes</h3>
    <div className="text-xs text-white/60 mb-2">{filePath}</div>
    <div className="bg-black/40 rounded-lg p-3 space-y-2">
      <div className="flex items-center space-x-2">
        <span className="text-red-400">-</span>
        <code className="text-red-300 text-sm">{before}</code>
      </div>
      <div className="flex items-center space-x-2">
        <span className="text-green-400">+</span>
        <code className="text-green-300 text-sm">{after}</code>
      </div>
    </div>
  </LiquidCard>
)

const ImageCompareBlock: React.FC<{ beforeUrl: string; afterUrl: string; caption?: string }> = ({
  beforeUrl,
  afterUrl,
  caption,
}) => {
  const [slider, setSlider] = useState(50)

  return (
    <LiquidCard variant="conversation">
      <h3 className="text-sm font-medium text-white/80 mb-3">Visual Changes</h3>
      <div className="relative bg-black/40 rounded-lg overflow-hidden">
        <div className="relative h-40">
          <img src={beforeUrl} alt="Before" className="absolute inset-0 w-full h-full object-cover" />
          <div
            className="absolute inset-0 overflow-hidden"
            style={{ clipPath: `inset(0 ${100 - slider}% 0 0)` }}
          >
            <img src={afterUrl} alt="After" className="w-full h-full object-cover" />
          </div>
        </div>
        <input
          type="range"
          min="0"
          max="100"
          value={slider}
          onChange={(e) => setSlider(Number(e.target.value))}
          className="absolute bottom-2 left-2 right-2 opacity-80"
        />
      </div>
      {caption && <p className="text-xs text-white/60 mt-2">{caption}</p>}
    </LiquidCard>
  )
}

const SpecSnippetBlock: React.FC<{ textMd: string; sourceId: string }> = ({ textMd, sourceId }) => (
  <LiquidCard variant="conversation">
    <h3 className="text-sm font-medium text-white/80 mb-3">Spec Reference</h3>
    <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3">
      <div className="prose prose-sm prose-invert max-w-none">
        <p className="text-white/90 text-sm">{textMd}</p>
      </div>
    </div>
    <div className="text-xs text-white/50 mt-2">From {sourceId}</div>
  </LiquidCard>
)

const LogExcerptBlock: React.FC<{ text: string; sourceId: string; level: 'info' | 'warn' | 'error' }> = ({
  text,
  sourceId,
  level,
}) => {
  const levelConfig = {
    info: { color: 'text-blue-300', bg: 'bg-blue-500/10' },
    warn: { color: 'text-amber-300', bg: 'bg-amber-500/10' },
    error: { color: 'text-red-300', bg: 'bg-red-500/10' },
  }

  return (
    <LiquidCard variant="conversation">
      <h3 className="text-sm font-medium text-white/80 mb-3">Log Output</h3>
      <div className={clsx('rounded-lg p-3', levelConfig[level].bg)}>
        <pre className={clsx('text-sm whitespace-pre-wrap', levelConfig[level].color)}>
          {text}
        </pre>
      </div>
      <div className="text-xs text-white/50 mt-2">From {sourceId}</div>
    </LiquidCard>
  )
}

const MetricBlock: React.FC<{ label: string; value: number; unit?: string; trend?: 'up' | 'down' | 'stable' }> = ({
  label,
  value,
  unit,
  trend,
}) => (
  <LiquidCard variant="conversation">
    <div className="flex items-center justify-between">
      <div>
        <h3 className="text-sm font-medium text-white/80">{label}</h3>
        <div className="flex items-center space-x-2 mt-1">
          <span className="text-xl font-bold text-white">{value}</span>
          {unit && <span className="text-sm text-white/60">{unit}</span>}
        </div>
      </div>
      {trend && (
        <div className={clsx(
          'flex items-center space-x-1 text-sm',
          trend === 'up' && 'text-green-400',
          trend === 'down' && 'text-red-400',
          trend === 'stable' && 'text-white/60'
        )}>
          {trend === 'up' && '↗'}
          {trend === 'down' && '↘'}
          {trend === 'stable' && '→'}
        </div>
      )}
    </div>
  </LiquidCard>
)

const LLMSuggestionBlock: React.FC<{ command: string; explanation: string; confidence: number }> = ({
  command,
  explanation,
  confidence,
}) => (
  <LiquidCard variant="conversation">
    <h3 className="text-sm font-medium text-white/80 mb-3">AI Suggestion</h3>
    <div className="space-y-3">
      <div className="bg-green-500/10 border border-green-500/20 rounded-lg p-3">
        <code className="text-green-300 text-sm">{command}</code>
      </div>
      <p className="text-sm text-white/90">{explanation}</p>
      <div className="flex items-center justify-between">
        <div className="text-xs text-white/60">Confidence: {Math.round(confidence * 100)}%</div>
        <div className="w-20 h-1 bg-white/20 rounded-full overflow-hidden">
          <div
            className="h-full bg-green-500 transition-all"
            style={{ width: `${confidence * 100}%` }}
          />
        </div>
      </div>
    </div>
  </LiquidCard>
)

const FileListBlock: React.FC<{ files: Array<{ path: string; status: 'added' | 'modified' | 'deleted'; additions: number; deletions: number }> }> = ({ files }) => (
  <LiquidCard variant="conversation">
    <h3 className="text-sm font-medium text-white/80 mb-3">Changed Files</h3>
    <div className="space-y-2">
      {files.map((file, i) => (
        <div key={i} className="flex items-center justify-between text-sm">
          <div className="flex items-center space-x-2">
            <span className={clsx(
              'w-2 h-2 rounded-full',
              file.status === 'added' && 'bg-green-500',
              file.status === 'modified' && 'bg-amber-500',
              file.status === 'deleted' && 'bg-red-500'
            )} />
            <span className="text-white/90">{file.path}</span>
          </div>
          <div className="flex items-center space-x-2 text-xs text-white/60">
            <span className="text-green-400">+{file.additions}</span>
            <span className="text-red-400">-{file.deletions}</span>
          </div>
        </div>
      ))}
    </div>
  </LiquidCard>
)

const TestResultsBlock: React.FC<{ results: Array<{ name: string; status: 'passed' | 'failed' | 'skipped'; duration: number; error?: string }> }> = ({ results }) => (
  <LiquidCard variant="conversation">
    <h3 className="text-sm font-medium text-white/80 mb-3">Test Results</h3>
    <div className="space-y-2">
      {results.map((result, i) => (
        <div key={i} className="flex items-center justify-between text-sm">
          <div className="flex items-center space-x-2">
            <span className={clsx(
              'text-xs',
              result.status === 'passed' && 'text-green-400',
              result.status === 'failed' && 'text-red-400',
              result.status === 'skipped' && 'text-white/60'
            )}>
              {result.status === 'passed' && '✓'}
              {result.status === 'failed' && '✗'}
              {result.status === 'skipped' && '○'}
            </span>
            <span className="text-white/90">{result.name}</span>
          </div>
          <span className="text-xs text-white/60">{result.duration}ms</span>
        </div>
      ))}
    </div>
  </LiquidCard>
)

const getCommandSuggestions = (input: string) => {
  const commands = [
    { command: '/fix', description: 'Fix the issue automatically' },
    { command: '/approve', description: 'Approve this change' },
    { command: '/reject', description: 'Reject this change' },
    { command: '/merge', description: 'Merge the pull request' },
    { command: '/deploy', description: 'Deploy to staging' },
    { command: '/rollback', description: 'Rollback to previous version' },
    { command: '/assign', description: 'Assign to someone' },
    { command: '/escalate', description: 'Escalate to team lead' },
  ]

  return commands.filter(cmd => cmd.command.includes(input.toLowerCase()))
}

export default ConversationColumn