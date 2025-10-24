import React from 'react'

interface FloatingChatButtonProps {
  onClick: () => void
  hasUnreadMessages?: boolean
}

const ChatIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
    <path 
      d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round"
    />
  </svg>
)

export const FloatingChatButton: React.FC<FloatingChatButtonProps> = ({ 
  onClick, 
  hasUnreadMessages = false 
}) => {
  return (
    <button
      className="nautex-floating-button"
      onClick={onClick}
      title="Chat with AI Assistant"
      style={{
        position: 'fixed',
        right: '24px',
        bottom: '24px',
        width: '56px',
        height: '56px',
        borderRadius: '50%',
        background: 'linear-gradient(135deg, #22c55e, #16a34a)',
        border: 'none',
        color: 'white',
        fontSize: '24px',
        cursor: 'pointer',
        boxShadow: '0 4px 16px rgba(34, 197, 94, 0.3)',
        transition: 'all 0.2s ease',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'scale(1.05)'
        e.currentTarget.style.boxShadow = '0 6px 20px rgba(34, 197, 94, 0.4)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'scale(1)'
        e.currentTarget.style.boxShadow = '0 4px 16px rgba(34, 197, 94, 0.3)'
      }}
    >
      ✨
      
      {/* Unread message indicator */}
      {hasUnreadMessages && (
        <div
          style={{
            position: 'absolute',
            top: '8px',
            right: '8px',
            width: '12px',
            height: '12px',
            background: '#FF4444',
            borderRadius: '50%',
            border: '2px solid #0b0f18',
            animation: 'pulse 2s infinite'
          }}
        />
      )}

      {/* Pulsing effect */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: '50%',
          background: 'linear-gradient(135deg, #15F1CC 0%, #00D4AA 100%)',
          opacity: 0.3,
          animation: 'ping 3s infinite'
        }}
      />
      
      <style jsx>{`
        @keyframes pulse {
          0% { opacity: 1; }
          50% { opacity: 0.5; }
          100% { opacity: 1; }
        }
        
        @keyframes ping {
          0% { transform: scale(1); opacity: 0.3; }
          50% { transform: scale(1.2); opacity: 0.1; }
          100% { transform: scale(1.4); opacity: 0; }
        }
        
        .floating-chat-btn:active {
          transform: scale(0.95) !important;
        }
      `}</style>
    </button>
  )
}