/**
 * MissionControlLayout - Main layout component for Mission Control
 * 
 * This component implements the three-column layout described in the spec:
 * - Left rail: Projects list with health indicators
 * - Center column: Decision feed with alerts and untriaged thoughts
 * - Right column: Contextual conversation panel
 * 
 * Why this layout exists:
 * - Provides the foundational structure for Mission Control
 * - Implements responsive behavior for mobile devices
 * - Manages the flow between different sections
 * - Creates the "foyer" experience described in the roadmap
 * 
 * For AI agents: This is the main container for Mission Control.
 * All three columns are managed here, with content passed as props.
 */

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { tokens } from '@/styles/tokens'
import { StageBar } from './StageBar'
import { ProjectRail } from './ProjectRail'
import { FeedColumn } from './FeedColumn'
import { ConversationColumn } from './ConversationColumn'
import { DefineStage } from '@/components/stages/DefineStage'
import { ThinkStage } from '@/components/stages/ThinkStage'
import type { ProjectSummary, FeedItem, ConversationPayload, SDLCStage } from '@/types'

interface MissionControlLayoutProps {
  // Data props
  projects: ProjectSummary[]
  feedItems: FeedItem[]
  conversation: ConversationPayload | null
  
  // State props
  selectedProject: string | null
  selectedFeedItem: string | null
  activeStage: SDLCStage
  
  // Handlers
  onProjectSelect: (projectId: string | null) => void
  onFeedItemSelect: (feedItemId: string | null) => void
  onStageChange: (stage: SDLCStage) => void
  onPromptSubmit: (prompt: string) => void
  onFeedItemAction: (feedItemId: string, action: string) => void
  onItemDrop?: (itemId: string, fromStage: SDLCStage, toStage: SDLCStage) => void
  
  // Loading states
  loading: {
    projects: boolean
    feed: boolean
    conversation: boolean
  }
  
  // Error states
  errors: {
    projects: string | null
    feed: string | null
    conversation: string | null
  }
}

export const MissionControlLayout: React.FC<MissionControlLayoutProps> = ({
  projects,
  feedItems,
  conversation,
  selectedProject,
  selectedFeedItem,
  activeStage,
  onProjectSelect,
  onFeedItemSelect,
  onStageChange,
  onPromptSubmit,
  onFeedItemAction,
  onItemDrop,
  loading,
  errors,
}) => {
  // Mobile responsive state
  const [isMobile, setIsMobile] = useState(false)
  const [showConversation, setShowConversation] = useState(false)
  const [railCollapsed, setRailCollapsed] = useState(false)

  // Check for mobile viewport
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768)
    }
    
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  // Auto-show conversation on mobile when item selected
  useEffect(() => {
    if (isMobile && selectedFeedItem) {
      setShowConversation(true)
    }
  }, [isMobile, selectedFeedItem])

  // Handle feed item selection
  const handleFeedItemSelect = (feedItemId: string | null) => {
    onFeedItemSelect(feedItemId)
    if (isMobile && feedItemId) {
      setShowConversation(true)
    }
  }

  // Handle back navigation on mobile
  const handleBackToFeed = () => {
    if (isMobile) {
      setShowConversation(false)
      onFeedItemSelect(null)
    }
  }

  return (
    <div className="h-screen text-white overflow-hidden">
      {/* Stage Bar - Always visible at top */}
      <StageBar
        activeStage={activeStage}
        onStageChange={onStageChange}
        showBackButton={isMobile && showConversation}
        onBackClick={handleBackToFeed}
        onItemDrop={onItemDrop}
        selectedProject={selectedProject}
      />

      {/* Main Content Area */}
      <div className="flex h-full pt-16">
        {/* Left Rail - Projects */}
        <AnimatePresence>
          {(!isMobile || !showConversation) && (
            <motion.div
              initial={{ x: -300, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: -300, opacity: 0 }}
              transition={{ duration: 0.3, ease: 'easeInOut' }}
              className={clsx(
                'bg-black/20 backdrop-blur-md border-r border-white/10',
                'flex-shrink-0 overflow-hidden',
                isMobile ? 'w-16' : railCollapsed ? 'w-16' : 'w-72',
                'transition-all duration-300'
              )}
            >
              <ProjectRail
                projects={projects}
                selectedProject={selectedProject}
                onProjectSelect={onProjectSelect}
                loading={loading.projects}
                error={errors.projects}
                collapsed={railCollapsed}
                onToggleCollapse={() => setRailCollapsed(!railCollapsed)}
                isMobile={isMobile}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Center Column - Stage Content */}
        <AnimatePresence>
          {(!isMobile || !showConversation) && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              className={clsx(
                'flex-1 min-w-0',
                'bg-black/10 backdrop-blur-sm',
                activeStage !== 'define' && 'border-r border-white/10',
                'overflow-hidden'
              )}
            >
              {activeStage === 'think' && (
                <ThinkStage
                  feedItems={feedItems}
                  selectedProject={selectedProject}
                  selectedFeedItem={selectedFeedItem}
                  onFeedItemSelect={handleFeedItemSelect}
                  onFeedItemAction={onFeedItemAction}
                  onStageChange={onStageChange}
                  loading={loading.feed}
                  error={errors.feed}
                />
              )}
              
              {activeStage === 'define' && (
                <DefineStage
                  feedItems={feedItems}
                  selectedProject={selectedProject}
                  selectedFeedItem={selectedFeedItem}
                  onFeedItemSelect={handleFeedItemSelect}
                  onStageChange={onStageChange}
                  loading={loading.feed}
                  error={errors.feed}
                />
              )}
              
              {activeStage === 'plan' && (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center text-white/60">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-white/5 flex items-center justify-center">
                      <span className="text-white/40 text-2xl">📋</span>
                    </div>
                    <h3 className="text-lg font-medium mb-2">Plan Stage</h3>
                    <p className="text-sm">Coming soon - Task planning and breakdown</p>
                  </div>
                </div>
              )}
              
              {activeStage === 'build' && (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center text-white/60">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-white/5 flex items-center justify-center">
                      <span className="text-white/40 text-2xl">🔨</span>
                    </div>
                    <h3 className="text-lg font-medium mb-2">Build Stage</h3>
                    <p className="text-sm">Coming soon - Development and coding</p>
                  </div>
                </div>
              )}
              
              {activeStage === 'validate' && (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center text-white/60">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-white/5 flex items-center justify-center">
                      <span className="text-white/40 text-2xl">✅</span>
                    </div>
                    <h3 className="text-lg font-medium mb-2">Validate Stage</h3>
                    <p className="text-sm">Coming soon - Testing and validation</p>
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Right Column - Conversation (only for Think stage) */}
        <AnimatePresence>
          {(!isMobile || showConversation) && selectedFeedItem && activeStage === 'think' && (
            <motion.div
              initial={{ x: 400, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: 400, opacity: 0 }}
              transition={{ duration: 0.3, ease: 'easeInOut' }}
              className={clsx(
                'bg-black/20 backdrop-blur-md',
                'overflow-hidden',
                isMobile ? 'w-full' : 'w-96',
                'border-l border-white/10'
              )}
            >
              <ConversationColumn
                conversation={conversation}
                onPromptSubmit={onPromptSubmit}
                loading={loading.conversation}
                error={errors.conversation}
                onClose={isMobile ? handleBackToFeed : undefined}
              />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Empty state when no item selected (only for Think stage) */}
        {!selectedFeedItem && (!isMobile || !showConversation) && activeStage === 'think' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="w-96 bg-black/10 backdrop-blur-sm border-l border-white/10 flex items-center justify-center"
          >
            <div className="text-center text-white/60 p-8">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-white/5 flex items-center justify-center">
                <svg
                  className="w-8 h-8"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-medium mb-2">Ready to Help</h3>
              <p className="text-sm">
                Select an item from the feed to see context and take action
              </p>
            </div>
          </motion.div>
        )}
      </div>

      {/* Liquid Glass Background Effects */}
      <div className="fixed inset-0 pointer-events-none -z-10">
        {/* Ambient background pattern */}
        <div 
          className="absolute inset-0 opacity-20"
          style={{
            backgroundImage: `radial-gradient(circle at 25% 25%, rgba(150, 179, 150, 0.1) 0%, transparent 50%),
                              radial-gradient(circle at 75% 75%, rgba(150, 179, 150, 0.1) 0%, transparent 50%)`,
          }}
        />
        
        {/* Floating glass orbs */}
        <motion.div
          className="absolute w-32 h-32 rounded-full bg-white/5 backdrop-blur-sm"
          style={{ top: '20%', left: '10%' }}
          animate={{
            y: [0, -20, 0],
            x: [0, 10, 0],
            scale: [1, 1.1, 1],
          }}
          transition={{
            duration: 6,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
        
        <motion.div
          className="absolute w-24 h-24 rounded-full bg-white/3 backdrop-blur-sm"
          style={{ top: '60%', right: '15%' }}
          animate={{
            y: [0, 15, 0],
            x: [0, -15, 0],
            scale: [1, 0.9, 1],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      </div>
    </div>
  )
}

export default MissionControlLayout