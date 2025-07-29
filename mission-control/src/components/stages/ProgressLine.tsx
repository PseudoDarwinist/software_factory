/**
 * ProgressLine - 4-dot progress indicator component
 * 
 * This component implements the 4-dot progress line shown in the mockup:
 * - 4 dots representing: Reading files → Pulling key points → Drafting PRD → Ready to review
 * - Smooth animations between progress states
 * - Status text updates corresponding to each dot
 * 
 * Requirements addressed:
 * - Requirement 4.1: 4-dot progress line with stages
 * - Requirement 4.2: Status text updates and smooth animations
 */

import React from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'

type ProcessingStage = 'idle' | 'reading' | 'extracting' | 'drafting' | 'ready'

interface ProgressLineProps {
  currentStage: ProcessingStage
  className?: string
}

interface ProgressStep {
  id: ProcessingStage
  label: string
  description: string
}

const progressSteps: ProgressStep[] = [
  {
    id: 'reading',
    label: 'Reading files',
    description: 'Processing uploaded documents and links'
  },
  {
    id: 'extracting',
    label: 'Pulling key points',
    description: 'Extracting relevant information and insights'
  },
  {
    id: 'drafting',
    label: 'Drafting PRD',
    description: 'Generating product requirements document'
  },
  {
    id: 'ready',
    label: 'Ready to review',
    description: 'PRD draft is complete and ready for review'
  }
]

export const ProgressLine: React.FC<ProgressLineProps> = ({
  currentStage,
  className,
}) => {
  // Get current step index
  const getCurrentStepIndex = () => {
    return progressSteps.findIndex(step => step.id === currentStage)
  }

  const currentStepIndex = getCurrentStepIndex()

  // Check if step is completed
  const isStepCompleted = (stepIndex: number) => {
    return stepIndex < currentStepIndex
  }

  // Check if step is current
  const isStepCurrent = (stepIndex: number) => {
    return stepIndex === currentStepIndex
  }

  // Get current step info
  const getCurrentStep = () => {
    return progressSteps[currentStepIndex] || progressSteps[0]
  }

  const currentStep = getCurrentStep()

  return (
    <div className={clsx('space-y-6', className)}>
      {/* Progress Line */}
      <div className="relative">
        {/* Background line */}
        <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-gray-700 transform -translate-y-1/2" />
        
        {/* Progress line */}
        <motion.div
          className="absolute top-1/2 left-0 h-0.5 bg-green-400 transform -translate-y-1/2"
          initial={{ width: '0%' }}
          animate={{ 
            width: currentStepIndex >= 0 ? `${((currentStepIndex + 1) / progressSteps.length) * 100}%` : '0%'
          }}
          transition={{ duration: 0.8, ease: 'easeInOut' }}
        />

        {/* Progress dots */}
        <div className="relative flex justify-between">
          {progressSteps.map((step, index) => (
            <motion.div
              key={step.id}
              className="relative flex flex-col items-center"
              initial={{ scale: 0.8, opacity: 0.5 }}
              animate={{ 
                scale: isStepCurrent(index) ? 1.2 : 1,
                opacity: isStepCompleted(index) || isStepCurrent(index) ? 1 : 0.5
              }}
              transition={{ duration: 0.5, ease: 'easeInOut' }}
            >
              {/* Dot */}
              <div
                className={clsx(
                  'w-4 h-4 rounded-full border-2 transition-all duration-500',
                  isStepCompleted(index) && 'bg-green-400 border-green-400',
                  isStepCurrent(index) && 'bg-green-400 border-green-400 shadow-lg shadow-green-400/50',
                  !isStepCompleted(index) && !isStepCurrent(index) && 'bg-gray-700 border-gray-600'
                )}
              >
                {/* Pulsing animation for current step */}
                {isStepCurrent(index) && (
                  <motion.div
                    className="absolute inset-0 rounded-full bg-green-400"
                    animate={{ 
                      scale: [1, 1.5, 1],
                      opacity: [0.5, 0, 0.5]
                    }}
                    transition={{ 
                      duration: 2,
                      repeat: Infinity,
                      ease: 'easeInOut'
                    }}
                  />
                )}

                {/* Checkmark for completed steps */}
                {isStepCompleted(index) && (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ duration: 0.3, delay: 0.2 }}
                    className="absolute inset-0 flex items-center justify-center"
                  >
                    <svg className="w-2.5 h-2.5 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </motion.div>
                )}
              </div>

              {/* Step label */}
              <motion.div
                className="mt-3 text-center"
                initial={{ opacity: 0, y: 10 }}
                animate={{ 
                  opacity: isStepCompleted(index) || isStepCurrent(index) ? 1 : 0.6,
                  y: 0
                }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
              >
                <p className={clsx(
                  'text-xs font-medium',
                  isStepCompleted(index) && 'text-green-400',
                  isStepCurrent(index) && 'text-green-400',
                  !isStepCompleted(index) && !isStepCurrent(index) && 'text-gray-400'
                )}>
                  {step.label}
                </p>
              </motion.div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Current step description */}
      <motion.div
        key={currentStep.id}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.5 }}
        className="text-center"
      >
        <h3 className="text-lg font-semibold text-green-400 mb-2">
          {currentStep.label}
        </h3>
        <p className="text-sm text-gray-400">
          {currentStep.description}
        </p>

        {/* Loading animation for current step */}
        {currentStepIndex >= 0 && currentStepIndex < progressSteps.length - 1 && (
          <motion.div
            className="mt-4 flex justify-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
          >
            <div className="flex space-x-1">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="w-2 h-2 bg-green-400 rounded-full"
                  animate={{
                    scale: [1, 1.2, 1],
                    opacity: [0.5, 1, 0.5]
                  }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    delay: i * 0.2,
                    ease: 'easeInOut'
                  }}
                />
              ))}
            </div>
          </motion.div>
        )}
      </motion.div>

      {/* Progress percentage */}
      <div className="text-center">
        <motion.div
          className="inline-flex items-center space-x-2 text-sm text-gray-400"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <span>Progress:</span>
          <motion.span
            className="font-medium text-green-400"
            key={currentStepIndex}
            initial={{ scale: 1.2 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.3 }}
          >
            {Math.round(((currentStepIndex + 1) / progressSteps.length) * 100)}%
          </motion.span>
        </motion.div>
      </div>
    </div>
  )
}

export default ProgressLine