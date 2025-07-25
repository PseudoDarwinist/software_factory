/**
 * AssistantSelector - Dropdown component for selecting AI assistants
 * 
 * This component provides a dropdown interface for users to choose between
 * different AI assistants (Claude Code and Kiro) for spec generation.
 * 
 * Features:
 * - Dropdown with Claude Code and Kiro options
 * - Automatic availability checking for Kiro
 * - Disabled state with tooltip when Kiro is unavailable
 * - Consistent styling with Mission Control design system
 * 
 * Requirements addressed:
 * - 1.1: Dropdown button instead of "Create Spec"
 * - 1.2: Options for "Claude Code" and "Kiro"
 * - 1.5: Disable Kiro option when not available with tooltip
 */

import React, { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { missionControlApi } from '@/services/api/missionControlApi'

export type AssistantType = 'claude' | 'kiro' | 'model-garden'

export interface AssistantOption {
  id: AssistantType
  name: string
  description: string
  available: boolean
  unavailableReason?: string
  logo: string
  gradient?: string
}

export interface AssistantSelectorProps {
  onAssistantSelect: (assistant: AssistantType) => void
  disabled?: boolean
  className?: string
  defaultAssistant?: AssistantType
}

export const AssistantSelector: React.FC<AssistantSelectorProps> = ({
  onAssistantSelect,
  disabled = false,
  className,
  defaultAssistant = 'claude'
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [selectedAssistant, setSelectedAssistant] = useState<AssistantType>(defaultAssistant)
  // Minimal assistant definitions (logo images are placed in mission-control/public)
  const [assistants, setAssistants] = useState<AssistantOption[]>([
    {
      id: 'claude',
      name: 'Claude Code',
      description: '', // description removed in minimalist UI
      available: true,
      logo: 'goose.png'
    },
    {
      id: 'model-garden',
      name: 'Model Garden',
      description: '',
      available: true,
      logo: 'coforge.png'
    },
    {
      id: 'kiro',
      name: 'Kiro',
      description: '',
      available: false,
      unavailableReason: 'Checking availability...',
      logo: 'kiro.png'
    }
  ])
  const [loading, setLoading] = useState(true)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Check Kiro availability on mount
  useEffect(() => {
    checkKiroAvailability()
  }, [])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const checkKiroAvailability = async () => {
    try {
      setLoading(true)
      
      // Call the Kiro status endpoint
      const response = await fetch('/api/kiro/status')
      const data = await response.json()
      
      console.log('Kiro status response:', data) // Debug log
      
      setAssistants(prev => {
        const updated = prev.map(assistant => {
          if (assistant.id === 'kiro') {
            return {
              ...assistant,
              available: data.available || false,
              unavailableReason: data.available 
                ? undefined 
                : 'Kiro IDE not found. Please install Kiro to use this option.'
            }
          }
          return assistant
        })
        console.log('Updated assistants:', updated) // Debug log
        return updated
      })
    } catch (error) {
      console.error('Failed to check Kiro availability:', error)
      setAssistants(prev => prev.map(assistant => {
        if (assistant.id === 'kiro') {
          return {
            ...assistant,
            available: false,
            unavailableReason: 'Unable to check Kiro availability. Please ensure Kiro is installed.'
          }
        }
        return assistant
      }))
    } finally {
      setLoading(false)
    }
  }

  const handleAssistantSelect = (assistantId: AssistantType) => {
    const assistant = assistants.find(a => a.id === assistantId)
    if (!assistant?.available) return

    setSelectedAssistant(assistantId)
    setIsOpen(false)
    onAssistantSelect(assistantId)
  }

  const selectedAssistantData = assistants.find(a => a.id === selectedAssistant)

  return (
    <div ref={dropdownRef} className={clsx('relative', className)}>
      {/* Main Button */}
      <motion.button
        whileHover={!disabled ? { scale: 1.02 } : {}}
        whileTap={!disabled ? { scale: 0.98 } : {}}
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={clsx(
          'flex items-center space-x-1 text-sm font-medium text-white/80',
          'transition-colors',
          !disabled && 'hover:text-white',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        <div className="flex items-center space-x-2">
          {selectedAssistantData && (
            <img
              src={selectedAssistantData.logo}
              alt={selectedAssistantData.name}
              className="w-5 h-5 object-contain"
              onError={(e) => {
                const target = e.target as HTMLImageElement;
                target.style.display = 'none';
              }}
            />
          )}
          <span className="font-medium text-sm text-white">{selectedAssistantData?.name || 'Select'}</span>
          {loading && (
            <div className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          )}
        </div>
        
        <motion.svg
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="w-3 h-3 text-white/60"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </motion.svg>
      </motion.button>

      {/* Dropdown Menu */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="absolute top-full left-0 right-0 mt-2 z-[100] min-w-[200px]"
          >
            <div className="bg-black/90 backdrop-blur-md border border-white/30 rounded-lg shadow-2xl overflow-hidden">
              {assistants.map((assistant) => {
                console.log('Rendering assistant:', assistant) // Debug log
                return (
                <div key={assistant.id} className="relative">
                  <motion.button
                    whileHover={assistant.available ? { backgroundColor: 'rgba(255, 255, 255, 0.08)' } : {}}
                    onClick={() => handleAssistantSelect(assistant.id)}
                    disabled={!assistant.available}
                    className={clsx(
                      'w-full px-3 py-2 text-left transition-all duration-150',
                      'flex items-center justify-between',
                      assistant.available 
                        ? 'text-white hover:bg-white/10 cursor-pointer' 
                        : 'text-white/50 cursor-not-allowed',
                      selectedAssistant === assistant.id && 'bg-blue-600/30'
                    )}
                  >
                    <div className="flex items-center space-x-3">
                      {/* Logo + Name */}
                      <div className="flex items-center space-x-3">
                        <img
                          src={assistant.logo}
                          alt={assistant.name}
                          className="w-12 h-12 object-contain"
                          onError={(e) => {
                            const target = e.target as HTMLImageElement;
                            target.style.display = 'none';
                          }}
                        />
                        <span className="text-sm text-white font-medium">{assistant.name}</span>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      {!assistant.available && (
                        <span className="text-xs text-red-400">Unavailable</span>
                      )}
                      {selectedAssistant === assistant.id && (
                        <svg className="w-3 h-3 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>
                  </motion.button>
                  
                  {/* Tooltip for unavailable assistants */}
                  {!assistant.available && assistant.unavailableReason && (
                    <div className="absolute left-0 top-full mt-1 px-3 py-2 bg-black/90 text-white text-xs rounded-md shadow-lg z-10 max-w-xs opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity">
                      {assistant.unavailableReason}
                    </div>
                  )}
                </div>
              )
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default AssistantSelector