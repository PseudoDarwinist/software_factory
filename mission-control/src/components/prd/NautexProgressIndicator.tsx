import React from 'react'
import './nautex-animations.css'

export interface NautexProgressIndicatorProps {
  stage: 'processing' | 'completed' | 'updating' | 'idle'
  progress: number // 0-100
  text: string
  showProgress?: boolean
}

export const NautexProgressIndicator: React.FC<NautexProgressIndicatorProps> = ({ 
  stage, 
  progress, 
  text, 
  showProgress = true 
}) => {
  if (stage === 'idle') return null

  const getStatusColor = () => {
    switch (stage) {
      case 'processing': return '#3b82f6'
      case 'completed': return '#10b981'
      case 'updating': return '#f59e0b'
      default: return '#6b7280'
    }
  }

  const getStatusBg = () => {
    switch (stage) {
      case 'processing': return '#dbeafe'
      case 'completed': return '#dcfce7'
      case 'updating': return '#fef3c7'
      default: return '#f3f4f6'
    }
  }

  return (
    <div style={{
      position: 'fixed',
      top: '80px',
      right: '24px',
      background: 'white',
      border: '1px solid rgba(229, 231, 235, 0.8)',
      borderRadius: '12px',
      padding: '16px',
      minWidth: '280px',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
      zIndex: 1000,
      animation: 'nautexSlideIn 0.3s ease-out'
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        marginBottom: showProgress ? '12px' : '0'
      }}>
        {/* Status indicator */}
        <div style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          background: getStatusColor(),
          animation: stage === 'processing' ? 'nautexPulse 2s infinite' : 'none'
        }} />
        
        {/* Status text */}
        <div style={{
          fontSize: '14px',
          fontWeight: 500,
          color: '#1f2937',
          flex: 1
        }}>
          {text}
        </div>

        {/* Status badge */}
        <div className={`nautex-status ${stage}`}>
          {stage === 'processing' && (
            <>
              <div className="nautex-typing-dots">
                <div className="nautex-typing-dot"></div>
                <div className="nautex-typing-dot"></div>
                <div className="nautex-typing-dot"></div>
              </div>
              Processing
            </>
          )}
          {stage === 'completed' && '✓ Complete'}
          {stage === 'updating' && '⟳ Updating'}
        </div>
      </div>

      {/* Progress bar */}
      {showProgress && progress > 0 && (
        <div className="nautex-progress-bar">
          <div 
            className={`nautex-progress-fill ${stage}`}
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {/* Completion message for successful operations */}
      {stage === 'completed' && (
        <div style={{
          fontSize: '12px',
          color: '#16a34a',
          marginTop: '8px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px'
        }}>
          <span>🎉</span>
          Document generated successfully
        </div>
      )}
    </div>
  )
}

export const NautexTypingIndicator: React.FC<{ 
  user?: string 
  show: boolean 
}> = ({ user = 'AI Assistant', show }) => {
  if (!show) return null

  return (
    <div className="nautex-typing" style={{
      position: 'fixed',
      bottom: '100px',
      right: '24px',
      zIndex: 1000,
      animation: 'nautexSlideIn 0.3s ease-out'
    }}>
      <div className="nautex-typing-dots">
        <div className="nautex-typing-dot"></div>
        <div className="nautex-typing-dot"></div>
        <div className="nautex-typing-dot"></div>
      </div>
      {user} is typing...
    </div>
  )
}

export const NautexSuccessToast: React.FC<{ 
  message: string
  show: boolean 
  onClose: () => void
}> = ({ message, show, onClose }) => {
  React.useEffect(() => {
    if (show) {
      const timer = setTimeout(onClose, 3000)
      return () => clearTimeout(timer)
    }
  }, [show, onClose])

  if (!show) return null

  return (
    <div style={{
      position: 'fixed',
      top: '24px',
      right: '24px',
      zIndex: 1000,
      animation: 'nautexSlideIn 0.3s ease-out'
    }}>
      <div className="nautex-success">
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px'
        }}>
          <span style={{ fontSize: '16px' }}>✅</span>
          <span>{message}</span>
          <button 
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: '#16a34a',
              cursor: 'pointer',
              marginLeft: 'auto',
              fontSize: '18px'
            }}
          >
            ×
          </button>
        </div>
      </div>
    </div>
  )
}