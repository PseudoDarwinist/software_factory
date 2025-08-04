/**
 * PRD Requirement Dialog - Shows when trying to move to Define stage without a frozen PRD
 * 
 * This dialog appears when users try to drag ideas to the Define stage but don't have
 * a frozen PRD for the project. It guides them through creating or uploading a PRD.
 */

import React, { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { useNavigate } from 'react-router-dom'

interface PrdRequirementDialogProps {
  isOpen: boolean
  onClose: () => void
  projectId: string
  itemId: string
  itemTitle: string
  prdStatus: 'missing' | 'draft' | 'frozen'
  uploadSessions: Array<{ id: string; description: string }>
  onPrdCreated?: () => void
}

export const PrdRequirementDialog: React.FC<PrdRequirementDialogProps> = ({
  isOpen,
  onClose,
  projectId,
  itemId,
  itemTitle,
  prdStatus,
  uploadSessions,
  onPrdCreated,
}) => {
  const [isCreatingPrd, setIsCreatingPrd] = useState(false)
  const navigate = useNavigate()

  const handleCreatePrd = useCallback(async () => {
    setIsCreatingPrd(true)
    
    try {
      // Import the API client
      const { missionControlApi } = await import('@/services/api/missionControlApi')
      
      // Create idea-specific PRD
      const result = await missionControlApi.createIdeaSpecificPrd(itemId, projectId)
      
      // Navigate to the PO interface to edit the PRD
      const poUrl = `/po.html?project=${projectId}&session=${result.upload_session_id}&context=edit_prd&item=${itemId}&title=${encodeURIComponent(itemTitle)}`
      window.open(poUrl, '_blank', 'width=1200,height=800')
      
      // Close this dialog
      onClose()
      
      // Optionally call callback to refresh data
      onPrdCreated?.()
      
    } catch (error) {
      console.error('Failed to create idea-specific PRD:', error)
      setIsCreatingPrd(false)
      // Could show error message to user here
    }
  }, [projectId, itemId, itemTitle, onClose, onPrdCreated])

  const handleUploadPrd = useCallback(() => {
    // Navigate to upload interface for this project
    const uploadUrl = `/business.html?project=${projectId}&mode=upload&context=prd_required`
    window.open(uploadUrl, '_blank', 'width=1200,height=800')
    onClose()
  }, [projectId, onClose])

  const handleUseDraftPrd = useCallback(() => {
    // If there's a draft PRD, guide user to freeze it
    if (uploadSessions.length > 0) {
      const latestSession = uploadSessions[0]
      const poUrl = `/po.html?project=${projectId}&session=${latestSession.id}&action=freeze_prd`
      window.open(poUrl, '_blank', 'width=1200,height=800')
      onClose()
    }
  }, [projectId, uploadSessions, onClose])

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        style={{ backgroundColor: 'rgba(0, 0, 0, 0.8)' }}
        onClick={onClose}
      >
        <motion.div
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.9, opacity: 0 }}
          className={clsx(
            'bg-gray-900 rounded-xl border border-gray-700',
            'p-6 max-w-md w-full mx-4',
            'backdrop-blur-sm'
          )}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-yellow-500/20 rounded-lg flex items-center justify-center">
                <span className="text-yellow-400 text-xl">📋</span>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-white">PRD Required</h3>
                <p className="text-sm text-gray-400">Product Requirements Document needed</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="mb-6">
            <p className="text-gray-300 mb-4">
              To move <strong>"{itemTitle}"</strong> to the Define stage, you need a frozen Product Requirements Document (PRD) that provides business context for spec generation.
            </p>

            {prdStatus === 'missing' && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 mb-4">
                <div className="flex items-start space-x-2">
                  <span className="text-red-400 text-lg">📋</span>
                  <div>
                    <p className="text-red-400 text-sm font-medium mb-1">No PRD Found</p>
                    <p className="text-red-300 text-xs">
                      Create a PRD to provide business context, target audience, goals, and requirements for this feature.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {prdStatus === 'draft' && (
              <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3 mb-4">
                <div className="flex items-start space-x-2">
                  <span className="text-yellow-400 text-lg">⏳</span>
                  <div>
                    <p className="text-yellow-400 text-sm font-medium mb-1">Draft PRD Available</p>
                    <p className="text-yellow-300 text-xs">
                      A draft PRD exists but needs to be reviewed and frozen before spec generation can proceed.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* PRD Architecture Explanation */}
            <div className="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 mb-4">
              <div className="flex items-start space-x-2">
                <span className="text-blue-400 text-lg">💡</span>
                <div>
                  <p className="text-blue-400 text-sm font-medium mb-1">Idea-Specific PRDs</p>
                  <p className="text-blue-300 text-xs">
                    Each idea gets its own PRD with business context, requirements, and supporting documents. 
                    This ensures DefineAgent generates specs with precise, relevant context for this specific feature.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div className="space-y-3">
            {prdStatus === 'missing' && (
              <>
                <button
                  onClick={handleCreatePrd}
                  disabled={isCreatingPrd}
                  className={clsx(
                    'w-full py-3 px-4 rounded-lg font-medium transition-all',
                    'bg-blue-600 hover:bg-blue-700 text-white',
                    'disabled:opacity-50 disabled:cursor-not-allowed'
                  )}
                >
                  {isCreatingPrd ? 'Creating Idea-Specific PRD...' : 'Create PRD for This Idea'}
                </button>
                
                <button
                  onClick={handleUploadPrd}
                  className={clsx(
                    'w-full py-3 px-4 rounded-lg font-medium transition-all',
                    'bg-gray-700 hover:bg-gray-600 text-white'
                  )}
                >
                  Upload Existing Documents
                </button>
              </>
            )}

            {prdStatus === 'draft' && uploadSessions.length > 0 && (
              <button
                onClick={handleUseDraftPrd}
                className={clsx(
                  'w-full py-3 px-4 rounded-lg font-medium transition-all',
                  'bg-yellow-600 hover:bg-yellow-700 text-white'
                )}
              >
                Review & Freeze Draft PRD
              </button>
            )}

            <button
              onClick={onClose}
              className={clsx(
                'w-full py-2 px-4 rounded-lg font-medium transition-all',
                'text-gray-400 hover:text-white hover:bg-gray-800'
              )}
            >
              Cancel
            </button>
          </div>

          {/* Help Text */}
          <div className="mt-4 pt-4 border-t border-gray-700">
            <p className="text-xs text-gray-500">
              A PRD defines the business requirements and context needed for generating accurate specifications.
              It should include problem statement, target audience, goals, and success metrics.
            </p>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

export default PrdRequirementDialog