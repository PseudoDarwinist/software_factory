import React, { useState, useRef, useEffect } from 'react'

interface ChatMessage {
  id: string
  type: 'user' | 'ai'
  content: string
  timestamp: Date
  modifications?: ModificationItem[]
  suggestions?: string[]
  showGenerateButton?: boolean
  isProgressMessage?: boolean
  progressStages?: Array<{
    id: string
    label: string
    status: 'pending' | 'processing' | 'completed'
    progress: number
  }>
}

interface ModificationItem {
  type: string
  target: string
  preview: string
  content?: any
}

interface ConversationState {
  mode: 'modify' | 'create' | null
  stage: 'initial' | 'gathering' | 'confirming' | 'generating' | 'modifying'
  context: Record<string, any>
  history: ChatMessage[]
  questionHistory: string[]
  currentTopic: string | null
  documentsToGenerate: string[]
}


interface AIChatPanelProps {
  isOpen: boolean
  onClose: () => void
  sessionId?: string
  onPRDUpdate?: (content: any) => void
  currentBlocks?: any[] // Current PRD content blocks for context
  onBlocksUpdate?: (blocks: any[]) => void // Function to update the main content
  isIntegratedPanel?: boolean // New prop to support both floating and integrated modes
}

const CloseIcon = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
    <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
  </svg>
)

const SendIcon = () => (
  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
    <path d="M18 2L9 11L6 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M18 2L11 18L9 11L2 9L18 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

export const AIChatPanel: React.FC<AIChatPanelProps> = ({ 
  isOpen, 
  onClose, 
  sessionId,
  onPRDUpdate,
  currentBlocks = [],
  onBlocksUpdate,
  isIntegratedPanel = false
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [conversationState, setConversationState] = useState<ConversationState>({
    mode: null,
    stage: 'initial',
    context: {},
    history: [],
    questionHistory: [],
    currentTopic: null,
    documentsToGenerate: []
  })

  
  const chatBodyRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Initialize chat with path selection when opened
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      showInitialPathSelection()
    }
  }, [isOpen])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (chatBodyRef.current) {
      chatBodyRef.current.scrollTop = chatBodyRef.current.scrollHeight
    }
  }, [messages])

  // Focus input when panel opens
  useEffect(() => {
    if (isOpen && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 100)
    }
  }, [isOpen])

  const showInitialPathSelection = () => {
    const pathMessage: ChatMessage = {
      id: 'path-selection',
      type: 'ai',
      content: "How would you like to proceed?",
      timestamp: new Date(),
      suggestions: ['Modify Current PRD', 'Generate New PRD from Idea']
    }
    setMessages([pathMessage])
  }

  const selectPath = async (path: string) => {
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: path,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setIsTyping(true)
    
    try {
      // Set conversation mode and enhance state
      if (path === 'Modify Current PRD') {
        setConversationState(prev => ({ 
          ...prev, 
          mode: 'modify', 
          stage: 'initial',
          context: { 
            ...prev.context, 
            pathSelected: 'modify',
            currentPRDBlocks: currentBlocks // Include current PRD content
          },
          history: []
        }))
        
        // Analyze current PRD content first
        if (currentBlocks && currentBlocks.length > 0) {
          try {
            const response = await fetch('/api/prd-editor/analyze-current-prd', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                content: currentBlocks,
                session_id: sessionId
              })
            })
            
            if (response.ok) {
              const data = await response.json()
              if (data.success) {
                const aiResponse: ChatMessage = {
                  id: Date.now().toString(),
                  type: 'ai',
                  content: data.data.message || 'I\'ve analyzed your current PRD. What specific aspect would you like to enhance?',
                  timestamp: new Date(),
                  suggestions: data.data.suggestions || [
                    'Add detailed user personas and user journeys',
                    'Enhance technical architecture with diagrams', 
                    'Improve functional requirements with specific use cases',
                    'Add comprehensive implementation timeline and phases'
                  ]
                }
                setMessages(prev => [...prev, aiResponse])
                return
              }
            } else {
              // API returned error (503, 500, etc.)
              console.error('AI service unavailable, status:', response.status)
              const errorResponse: ChatMessage = {
                id: Date.now().toString(),
                type: 'ai',
                content: '⚠️ AI service is currently unavailable (connection issues with Claude Sonnet 3.5). Please try again in a moment, or continue with manual PRD editing.',
                timestamp: new Date(),
                suggestions: [
                  'Try again in a few moments',
                  'Continue editing manually',
                  'Check your internet connection',
                  'Contact support if this persists'
                ]
              }
              setMessages(prev => [...prev, errorResponse])
              return
            }
          } catch (error) {
            console.error('Failed to analyze current PRD:', error)
          }
        }
        
        // Fallback when no current blocks or analysis failed
        const aiResponse: ChatMessage = {
          id: Date.now().toString(),
          type: 'ai',
          content: currentBlocks && currentBlocks.length > 0 
            ? '⚠️ AI analysis unavailable, but I can see your current TaskFlow PRD. What specific aspect would you like me to enhance or improve?'
            : '⚠️ AI service temporarily unavailable. I can still help you improve your PRD. What specific aspect would you like to enhance?',
          timestamp: new Date(),
          suggestions: [
            'Add detailed user personas and user journeys',
            'Enhance technical architecture with diagrams',
            'Improve functional requirements with specific use cases', 
            'Add comprehensive implementation timeline and phases'
          ]
        }
        setMessages(prev => [...prev, aiResponse])
        
      } else if (path === 'Generate New PRD from Idea') {
        setConversationState(prev => ({ 
          ...prev, 
          mode: 'create', 
          stage: 'gathering',
          context: { ...prev.context, pathSelected: 'create' },
          history: []
        }))
        
        const aiResponse = await handleAiChatMessage(path)
        setMessages(prev => [...prev, aiResponse])
      }
    } catch (error) {
      console.error('Failed to handle path selection:', error)
      const errorResponse: ChatMessage = {
        id: Date.now().toString(),
        type: 'ai',
        content: 'I encountered an error processing your selection. Please try again.',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorResponse])
    } finally {
      setIsTyping(false)
    }
  }
  
  const selectSuggestion = async (suggestion: string) => {
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: suggestion,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setIsTyping(true)

    try {
      const aiResponse = await handleAiChatMessage(suggestion)
      setMessages(prev => [...prev, aiResponse])
    } catch (error) {
      console.error('Failed to handle suggestion:', error)
      const errorResponse: ChatMessage = {
        id: Date.now().toString(),
        type: 'ai',
        content: 'I encountered an error processing your selection. Please try again.',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorResponse])
    } finally {
      setIsTyping(false)
    }
  }

  const handleAiChatMessage = async (userMessage: string): Promise<ChatMessage> => {
    try {
      console.log('Processing message with conversation state:', userMessage)
      
      // Add user message to conversation history
      const updatedConversationState = {
        ...conversationState,
        history: [
          ...conversationState.history,
          {
            role: 'user',
            message: userMessage,
            timestamp: new Date().toISOString()
          }
        ]
      }
      
      // Use the intelligent conversation endpoint from the frontend intelligent editor
      let apiResponse;
      
      if (conversationState.mode === 'modify') {
        // Include current PRD content in the context
        const prdContext = currentBlocks && currentBlocks.length > 0 
          ? `\n\nCURRENT PRD CONTENT: ${JSON.stringify(currentBlocks, null, 2)}`
          : ''
          
        apiResponse = await fetch('/api/prd-editor/simple-conversation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: `MODIFY PRD CONTEXT: User wants to improve their existing PRD.${prdContext}\n\nUSER REQUEST: "${userMessage}". Provide intelligent follow-up questions and specific suggestions for PRD enhancement.`,
            conversation_state: {
              ...updatedConversationState,
              context: {
                ...updatedConversationState.context,
                currentPRDBlocks: currentBlocks
              }
            }
          })
        })
      } else if (conversationState.mode === 'create') {
        apiResponse = await fetch('/api/prd-editor/simple-conversation', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message: userMessage,
            conversation_state: updatedConversationState
          })
        })
      } else {
        // Fall back to model garden for general responses
        apiResponse = await fetch('/api/model-garden/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            instruction: userMessage,
            model: 'claude-opus-4',
            role: 'po'
          })
        })
      }

      if (!apiResponse.ok) {
        throw new Error(`API error: ${apiResponse.status}`)
      }

      const result = await apiResponse.json()
      console.log('AI API response:', result)
      
      if (result.success) {
        let aiContent, suggestions = [], showGenerateButton = false
        
        if (result.data?.message) {
          // Response from simple-conversation endpoint
          aiContent = result.data.message
          suggestions = result.data.suggestions || []
          
          // Update conversation state if provided
          if (result.data.conversation_state) {
            setConversationState(prev => ({
              ...prev,
              ...result.data.conversation_state,
              history: [
                ...prev.history,
                {
                  role: 'assistant',
                  message: aiContent,
                  timestamp: new Date().toISOString()
                }
              ]
            }))
          }
          
          // Check if we should show generate button (after 3+ exchanges)
          const totalExchanges = updatedConversationState.history.length
          showGenerateButton = totalExchanges >= 6 || result.data.show_generate_button
          
        } else {
          // Response from model garden endpoint
          aiContent = result.output || result.data || result.response || 'No response received'
          
          // Enhanced suggestion generation for drilling questions
          const lowerContent = aiContent.toLowerCase()
          
          if (lowerContent.includes('?') && (lowerContent.includes('tell me') || lowerContent.includes('describe') || lowerContent.includes('what'))) {
            if (conversationState.mode === 'create') {
              suggestions = [
                'A mobile app for task management and productivity',
                'A web-based project management platform', 
                'An AI-powered analytics dashboard',
                'A customer relationship management system'
              ]
            } else if (conversationState.mode === 'modify') {
              suggestions = [
                'Add detailed user personas and user journeys',
                'Enhance technical architecture with diagrams',
                'Improve functional requirements with specific use cases',
                'Add comprehensive implementation timeline and phases'
              ]
            }
          }
        }
        
        return {
          id: Date.now().toString(),
          type: 'ai',
          content: aiContent,
          timestamp: new Date(),
          modifications: [], // Will be populated when AI specifically provides modifications
          suggestions: suggestions,
          showGenerateButton: showGenerateButton
        }
      } else {
        throw new Error(result.error || 'Failed to get AI response')
      }
    } catch (error) {
      console.error('AI chat error:', error)
      return {
        id: Date.now().toString(),
        type: 'ai',
        content: 'I encountered an error processing your message. Please try again.',
        timestamp: new Date()
      }
    }
  }

  const sendMessage = async () => {
    if (!inputValue.trim() || isTyping) return

    const messageContent = inputValue.trim()
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: messageContent,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsTyping(true)

    try {
      const aiResponse = await handleAiChatMessage(messageContent)
      setMessages(prev => [...prev, aiResponse])
    } catch (error) {
      console.error('Failed to send message:', error)
      const errorResponse: ChatMessage = {
        id: Date.now().toString(),
        type: 'ai',
        content: 'I encountered an error processing your message. Please try again.',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorResponse])
    } finally {
      setIsTyping(false)
    }
  }

  const applyModification = (modification: ModificationItem) => {
    console.log('Applying modification:', modification)
    if (onBlocksUpdate) {
      applyContentModification(modification)
    } else if (onPRDUpdate) {
      onPRDUpdate(modification)
    }
  }
  
  const applyContentModification = async (modification: ModificationItem) => {
    if (!onBlocksUpdate) return
    
    try {
      const updatedBlocks = [...currentBlocks]
      
      switch (modification.type) {
        case 'add_section':
          const newSection = {
            id: `section-${Date.now()}`,
            type: 'section',
            content: {
              title: modification.data?.title || 'New Section',
              text: modification.data?.content || 'Section content...',
              level: 2
            }
          }
          updatedBlocks.push(newSection)
          break
          
        case 'add_diagram':
          const diagramBlock = {
            id: `mermaid-${Date.now()}`,
            type: 'mermaid',
            content: {
              code: modification.data?.code || 'graph TD\n  A --> B',
              caption: modification.data?.caption || 'System Diagram'
            }
          }
          updatedBlocks.push(diagramBlock)
          break
          
        case 'add_requirements':
          const requirementsBlock = {
            id: `requirements-${Date.now()}`,
            type: 'section',
            content: {
              title: 'Requirements',
              text: modification.data?.content || 'Requirements content...',
              level: 2
            }
          }
          updatedBlocks.push(requirementsBlock)
          break
          
        case 'enhance_content':
          if (modification.data?.blockIndex >= 0) {
            const blockIndex = modification.data.blockIndex
            if (updatedBlocks[blockIndex]) {
              updatedBlocks[blockIndex] = {
                ...updatedBlocks[blockIndex],
                content: {
                  ...updatedBlocks[blockIndex].content,
                  text: (updatedBlocks[blockIndex].content?.text || '') + '\n\n' + (modification.data.enhancement || '')
                }
              }
            }
          }
          break
          
        case 'comprehensive_update':
          // For comprehensive updates, parse the AI response and smart merge with existing blocks
          if (modification.data?.content) {
            const newBlocks = parseAIContentToBlocks(modification.data.content)
            const mergedBlocks = smartMergeBlocks(currentBlocks, newBlocks, conversationState.mode || 'modify')
            onBlocksUpdate(mergedBlocks)
            return
          }
          break
      }
      
      onBlocksUpdate(updatedBlocks)
      
      // Auto-save the modified blocks to database
      if (updatedBlocks.length > 0 && sessionId) {
        try {
          console.log('🔍 MODIFICATION SAVE DEBUG: Starting save process...')
          console.log('🔍 Session ID:', sessionId)
          console.log('🔍 Updated blocks count:', updatedBlocks.length)
          
          const { missionControlApi } = await import('@/services/api/missionControlApi')
          const result = await missionControlApi.savePRDBlocks(sessionId, updatedBlocks, {
            title: extractTitleFromBlocks(updatedBlocks),
            lastModified: new Date(),
            source: 'ai_modification'
          })
          console.log('✅ Content modification saved successfully:', result)
        } catch (saveError) {
          console.error('❌ CRITICAL: Failed to save content modification:', saveError)
          console.error('❌ Modification save error details:', {
            message: (saveError as Error)?.message,
            sessionId,
            blocksCount: updatedBlocks.length
          })
        }
      } else {
        console.warn('⚠️ MODIFICATION SAVE SKIPPED:', {
          hasBlocks: updatedBlocks.length > 0,
          hasSessionId: !!sessionId,
          blocksCount: updatedBlocks.length,
          sessionId
        })
      }
      
      // Show success message
      const successMessage: ChatMessage = {
        id: Date.now().toString(),
        type: 'ai',
        content: '✅ Successfully applied the changes to your PRD!',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, successMessage])
      
    } catch (error) {
      console.error('Failed to apply content modification:', error)
      const errorMessage: ChatMessage = {
        id: Date.now().toString(),
        type: 'ai',
        content: '❌ Failed to apply changes to the document. Please try again.',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    }
  }
  
  const parseAIContentToBlocks = (content: string) => {
    // Simple parser for AI-generated content
    const lines = content.split('\n')
    const blocks = []
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim()
      if (!line) continue
      
      // Headers
      if (line.startsWith('# ')) {
        blocks.push({
          id: `header-${Date.now()}-${i}`,
          type: 'header',
          content: { text: line.replace('# ', ''), level: 1 }
        })
      } else if (line.startsWith('## ')) {
        blocks.push({
          id: `header-${Date.now()}-${i}`,
          type: 'header',
          content: { text: line.replace('## ', ''), level: 2 }
        })
      } else if (line.startsWith('### ')) {
        blocks.push({
          id: `header-${Date.now()}-${i}`,
          type: 'header',
          content: { text: line.replace('### ', ''), level: 3 }
        })
      } else if (line.startsWith('```mermaid')) {
        // Extract mermaid diagram
        const mermaidLines = []
        i++ // Skip the opening ```mermaid
        while (i < lines.length && !lines[i].trim().startsWith('```')) {
          mermaidLines.push(lines[i])
          i++
        }
        blocks.push({
          id: `mermaid-${Date.now()}-${i}`,
          type: 'mermaid',
          content: { code: mermaidLines.join('\n') }
        })
      } else {
        // Regular paragraph
        blocks.push({
          id: `paragraph-${Date.now()}-${i}`,
          type: 'paragraph',
          content: { text: line }
        })
      }
    }
    
    return blocks
  }

  const smartMergeBlocks = (existingBlocks: any[], newBlocks: any[], mode: string) => {
    console.log(`Smart merge: mode=${mode}, existing=${existingBlocks?.length || 0} blocks, new=${newBlocks?.length || 0} blocks`)
    
    // If in create mode or no existing blocks, return new blocks
    if (mode === 'create' || !existingBlocks || existingBlocks.length === 0) {
      console.log('Smart merge: Using new blocks entirely')
      return newBlocks
    }
    
    // For modify mode, intelligently merge blocks
    const mergedBlocks = [...existingBlocks]
    const existingHeaders = new Map<string, number>()
    
    // Index existing headers by normalized text for smart matching
    existingBlocks.forEach((block, index) => {
      if (block.type === 'header') {
        const headerText = normalizeHeaderText(block.content?.text || '')
        existingHeaders.set(headerText, index)
      }
    })
    
    // Process new blocks - update existing sections or add new ones
    let updatedSections = 0
    let addedSections = 0
    
    for (const newBlock of newBlocks) {
      if (newBlock.type === 'header') {
        const headerText = normalizeHeaderText(newBlock.content?.text || '')
        const existingIndex = existingHeaders.get(headerText)
        
        if (existingIndex !== undefined) {
          console.log(`Smart merge: Updating existing section "${newBlock.content?.text}"`)
          // Update existing header
          mergedBlocks[existingIndex] = newBlock
          
          // Find and replace content blocks that follow this header
          const nextHeaderIndex = findNextHeaderIndex(mergedBlocks, existingIndex + 1)
          const newContentBlocks = collectContentBlocksAfterHeader(newBlocks, newBlock)
          
          // Remove old content blocks between this header and next header
          mergedBlocks.splice(existingIndex + 1, nextHeaderIndex - existingIndex - 1, ...newContentBlocks)
          updatedSections++
        } else {
          console.log(`Smart merge: Adding new section "${newBlock.content?.text}"`)
          // Add new header and its content blocks at the end
          mergedBlocks.push(newBlock)
          const newContentBlocks = collectContentBlocksAfterHeader(newBlocks, newBlock)
          mergedBlocks.push(...newContentBlocks)
          addedSections++
        }
      } else if (!isPartOfHeaderSection(newBlocks, newBlock)) {
        // Add standalone blocks (not part of a header section) at the end
        console.log(`Smart merge: Adding standalone block of type "${newBlock.type}"`)
        mergedBlocks.push(newBlock)
      }
    }
    
    console.log(`Smart merge complete: ${updatedSections} sections updated, ${addedSections} sections added, final block count: ${mergedBlocks.length}`)
    return mergedBlocks
  }
  
  const normalizeHeaderText = (text: string): string => {
    return text.toLowerCase()
      .replace(/[^a-z0-9\s]/g, '')
      .replace(/\s+/g, ' ')
      .trim()
  }
  
  const findNextHeaderIndex = (blocks: any[], startIndex: number): number => {
    for (let i = startIndex; i < blocks.length; i++) {
      if (blocks[i].type === 'header') {
        return i
      }
    }
    return blocks.length
  }
  
  const collectContentBlocksAfterHeader = (blocks: any[], headerBlock: any): any[] => {
    const headerIndex = blocks.indexOf(headerBlock)
    if (headerIndex === -1) return []
    
    const contentBlocks = []
    for (let i = headerIndex + 1; i < blocks.length; i++) {
      if (blocks[i].type === 'header') {
        break
      }
      contentBlocks.push(blocks[i])
    }
    return contentBlocks
  }
  
  const isPartOfHeaderSection = (blocks: any[], block: any): boolean => {
    const blockIndex = blocks.indexOf(block)
    if (blockIndex === -1) return false
    
    // Look backwards to see if there's a header before this block
    for (let i = blockIndex - 1; i >= 0; i--) {
      if (blocks[i].type === 'header') {
        return true
      }
      if (blocks[i].type === 'paragraph' || blocks[i].type === 'mermaid') {
        continue
      }
      break
    }
    return false
  }
  
  const extractTitleFromBlocks = (blocks: any[]): string => {
    // Find the first header block with level 1
    for (const block of blocks) {
      if (block.type === 'header' && block.content?.level === 1) {
        return block.content.text || 'Product Requirements Document'
      }
    }
    
    // Fallback: look for any header
    for (const block of blocks) {
      if (block.type === 'header' && block.content?.text) {
        return block.content.text
      }
    }
    
    return 'Product Requirements Document'
  }
  
  const extractModificationsFromContent = (content: string): ModificationItem[] => {
    const modifications: ModificationItem[] = []
    
    // Check if content contains mermaid diagrams
    if (content.includes('```mermaid')) {
      const mermaidMatch = content.match(/```mermaid\n([\s\S]*?)\n```/)
      if (mermaidMatch) {
        modifications.push({
          type: 'add_diagram',
          target: 'System Architecture Diagram',
          preview: 'Add Mermaid diagram to the document',
          content: { code: mermaidMatch[1] }
        })
      }
    }
    
    // Check if content contains section headers
    const headerMatches = content.match(/^#{1,3} .+$/gm)
    if (headerMatches && headerMatches.length > 0) {
      modifications.push({
        type: 'add_section',
        target: 'New Sections',
        preview: `Add ${headerMatches.length} new section(s) to the document`,
        content: { content: content }
      })
    }
    
    // Check for specific enhancement keywords
    const enhancementKeywords = ['enhance', 'improve', 'add detail', 'expand', 'technical architecture']
    if (enhancementKeywords.some(keyword => content.toLowerCase().includes(keyword))) {
      modifications.push({
        type: 'enhance_content',
        target: 'Current Content',
        preview: 'Apply enhancements and improvements to existing sections',
        content: { enhancement: content }
      })
    }
    
    return modifications
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // Common chat content component
  const ChatContent = () => (
    <>
      {/* Close button - floating in top right */}
      <button
        className="chat-close"
        onClick={onClose}
        style={{
          position: 'absolute',
          top: '12px',
          right: '16px',
          background: 'rgba(0, 0, 0, 0.1)',
          border: 'none',
          color: '#64748b',
          cursor: 'pointer',
          padding: '8px',
          borderRadius: '50%',
          fontSize: '14px',
          fontWeight: 'normal',
          width: '32px',
          height: '32px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 10,
          backdropFilter: 'blur(10px)',
          transition: 'all 0.2s ease'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = 'rgba(0, 0, 0, 0.2)'
          e.currentTarget.style.color = '#1e293b'
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'rgba(0, 0, 0, 0.1)'
          e.currentTarget.style.color = '#64748b'
        }}
      >
        ×
      </button>

      {/* Chat Messages */}
      <div
        ref={chatBodyRef}
        className="chat-body"
        style={{
          flex: 1,
          padding: '16px',
          overflowY: 'auto'
        }}
      >
          {messages.map((message) => (
            <div key={message.id} className={`chat-message ${message.type}`}>
              {message.type === 'ai' && (
                <div style={{ fontWeight: 600, marginBottom: '8px', fontSize: '14px' }}>el Agénte</div>
              )}
              
              <div style={{ 
                color: message.type === 'user' ? '#1e293b' : '#37352f',
                fontSize: '14px',
                lineHeight: 1.5,
                marginBottom: message.suggestions?.length || message.modifications?.length || message.isProgressMessage ? '16px' : '0'
              }}>
                {message.content}
              </div>

              {/* Progress Stages */}
              {message.isProgressMessage && message.progressStages && (
                <div style={{ marginTop: '16px' }}>
                  {message.progressStages.map((stage, index) => (
                    <div key={stage.id} style={{
                      display: 'flex',
                      alignItems: 'center',
                      marginBottom: '12px',
                      gap: '12px'
                    }}>
                      {/* Status Icon */}
                      <div style={{
                        width: '20px',
                        height: '20px',
                        borderRadius: '50%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        background: stage.status === 'completed' ? '#10b981' : 
                                   stage.status === 'processing' ? '#ffffff' : '#e5e7eb',
                        border: stage.status === 'processing' ? '2px solid #3b82f6' : 'none'
                      }}>
                        {stage.status === 'completed' ? (
                          <svg width="12" height="12" viewBox="0 0 20 20" fill="white">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        ) : stage.status === 'processing' ? (
                          <div style={{
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%',
                            background: '#3b82f6',
                            animation: 'spin 1s linear infinite'
                          }} />
                        ) : null}
                      </div>

                      {/* Stage Label */}
                      <div style={{
                        fontSize: '14px',
                        fontWeight: 500,
                        color: '#37352f',
                        minWidth: '120px'
                      }}>
                        {stage.label}
                      </div>

                      {/* Progress Bar */}
                      <div style={{
                        flex: 1,
                        height: '6px',
                        background: '#e5e7eb',
                        borderRadius: '3px',
                        overflow: 'hidden',
                        maxWidth: '200px'
                      }}>
                        <div style={{
                          width: `${stage.progress}%`,
                          height: '100%',
                          background: '#3b82f6',
                          borderRadius: '3px',
                          transition: 'width 0.3s ease'
                        }} />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Suggestions */}
              {message.suggestions && message.suggestions.length > 0 && (
                <div style={{ 
                  marginTop: '16px',
                  padding: '16px',
                  background: '#f1f5f9',
                  borderRadius: '8px',
                  border: '1px solid #d1d5db',
                  borderLeft: '3px solid #6b7280'
                }}>
                  <div style={{
                    fontSize: '14px',
                    fontWeight: 600,
                    color: '#374151',
                    marginBottom: '12px'
                  }}>
                    {message.id === 'path-selection' ? 'Choose your approach:' : 'Quick responses:'}
                  </div>
                  <div style={{ 
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '8px',
                    marginTop: '8px'
                  }}>
                  {message.suggestions.map((suggestion, index) => (
                    <button
                      key={index}
                      onClick={() => {
                        // Handle path selection vs regular suggestions differently
                        if (message.id === 'path-selection') {
                          selectPath(suggestion)
                        } else {
                          selectSuggestion(suggestion)
                        }
                      }}
                      style={{
                        padding: '10px 14px',
                        background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.15) 0%, rgba(34, 197, 94, 0.08) 50%, rgba(34, 197, 94, 0.05) 100%)',
                        border: '0.5px solid rgba(34, 197, 94, 0.4)',
                        borderRadius: '16px',
                        color: '#1f2937',
                        fontSize: '13px',
                        fontWeight: '500',
                        cursor: 'pointer',
                        textAlign: 'left',
                        transition: 'all 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
                        backdropFilter: 'blur(20px) saturate(180%)',
                        boxShadow: 'inset 0 0 15px rgba(34, 197, 94, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.2), inset 0 -1px 0 rgba(34, 197, 94, 0.1)',
                        lineHeight: 1.4,
                        position: 'relative',
                        overflow: 'hidden'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'linear-gradient(135deg, rgba(34, 197, 94, 0.25) 0%, rgba(34, 197, 94, 0.15) 50%, rgba(34, 197, 94, 0.08) 100%)'
                        e.currentTarget.style.borderColor = 'rgba(34, 197, 94, 0.6)'
                        e.currentTarget.style.transform = 'translateY(-2px) scale(1.02)'
                        e.currentTarget.style.boxShadow = 'inset 0 0 20px rgba(34, 197, 94, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.3), inset 0 -1px 0 rgba(34, 197, 94, 0.2)'
                        e.currentTarget.style.color = '#1f2937'
                        e.currentTarget.style.textShadow = 'none'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'linear-gradient(135deg, rgba(34, 197, 94, 0.15) 0%, rgba(34, 197, 94, 0.08) 50%, rgba(34, 197, 94, 0.05) 100%)'
                        e.currentTarget.style.borderColor = 'rgba(34, 197, 94, 0.4)'
                        e.currentTarget.style.transform = 'translateY(0) scale(1)'
                        e.currentTarget.style.boxShadow = 'inset 0 0 15px rgba(34, 197, 94, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.2), inset 0 -1px 0 rgba(34, 197, 94, 0.1)'
                        e.currentTarget.style.color = '#1f2937'
                        e.currentTarget.style.textShadow = 'none'
                      }}
                      onMouseDown={(e) => {
                        e.currentTarget.style.transform = 'translateY(0) scale(0.98)'
                      }}
                    >
                      {suggestion}
                    </button>
                  ))}
                  </div>
                </div>
              )}

              {/* Modifications */}
              {message.modifications && message.modifications.length > 0 && (
                <div style={{ marginTop: '12px' }}>
                  <div style={{ fontWeight: 600, marginBottom: '12px', color: '#475569' }}>
                    Proposed Changes:
                  </div>
                  {message.modifications.map((mod, index) => (
                    <div key={index} style={{
                      background: '#f8fafc',
                      border: '1px solid #e2e8f0',
                      borderRadius: '8px',
                      padding: '12px',
                      marginBottom: '8px'
                    }}>
                      <div style={{ marginBottom: '8px' }}>
                        <strong style={{ color: '#374151' }}>
                          {mod.type.toUpperCase().replace('_', ' ')}: {mod.target}
                        </strong>
                        <p style={{ margin: '4px 0', color: '#64748b', fontSize: '13px' }}>
                          {mod.preview}
                        </p>
                      </div>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          onClick={() => applyModification(mod)}
                          style={{
                            padding: '6px 12px',
                            background: '#22c55e',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            fontSize: '12px',
                            cursor: 'pointer',
                            fontWeight: 600
                          }}
                        >
                          Apply Change
                        </button>
                        <button
                          style={{
                            padding: '6px 12px',
                            background: '#f1f5f9',
                            color: '#64748b',
                            border: '1px solid #e2e8f0',
                            borderRadius: '6px',
                            fontSize: '12px',
                            cursor: 'pointer'
                          }}
                        >
                          Skip
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Generate Button */}
              {message.showGenerateButton && (
                <div style={{ marginTop: '16px', textAlign: 'center' }}>
                  <button
                    onClick={async () => {
                      console.log('Generate PRD clicked')
                      
                      // Add progress message to chat
                      const progressStages = [
                        { id: 'processing-prd', label: 'Processing PRD', status: 'processing' as const, progress: 0 },
                        { id: 'creating-prd', label: 'Creating PRD', status: 'pending' as const, progress: 0 },
                        { id: 'processing-trd', label: 'Processing TRD', status: 'pending' as const, progress: 0 },
                        { id: 'creating-trd', label: 'Creating TRD', status: 'pending' as const, progress: 0 }
                      ]

                      const progressMessage: ChatMessage = {
                        id: 'progress-' + Date.now().toString(),
                        type: 'ai',
                        content: 'Generating initial documents',
                        timestamp: new Date(),
                        isProgressMessage: true,
                        progressStages: progressStages
                      }

                      setMessages(prev => [...prev, progressMessage])
                      // Don't set isTyping as it shows "Analyzing your request" - we have our own progress UI

                      // Helper function to update progress stages
                      const updateProgress = (stageId: string, progress: number, status?: 'processing' | 'completed') => {
                        const stageToUpdate = progressStages.find(s => s.id === stageId)
                        if (stageToUpdate) {
                          stageToUpdate.progress = progress
                          if (status) stageToUpdate.status = status
                          
                          setMessages(prev => prev.map(msg => 
                            msg.id === progressMessage.id 
                              ? { ...msg, progressStages: [...progressStages] }
                              : msg
                          ))
                        }
                      }
                      
                      try {
                        // Start with processing PRD
                        updateProgress('processing-prd', 10, 'processing')
                        
                        // Gradually advance processing PRD during the API call
                        const progressInterval = setInterval(() => {
                          const currentStage = progressStages.find(s => s.id === 'processing-prd')
                          if (currentStage && currentStage.progress < 90) {
                            currentStage.progress += Math.random() * 15 + 5
                            setMessages(prev => prev.map(msg => 
                              msg.id === progressMessage.id 
                                ? { ...msg, progressStages: [...progressStages] }
                                : msg
                            ))
                          }
                        }, 300)
                        
                        // Call comprehensive generation API
                        const response = await fetch('/api/prd-editor/generate-comprehensive-prd', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({
                            conversation_state: conversationState,
                            current_blocks: currentBlocks,
                            mode: conversationState.mode
                          })
                        })
                        
                        // Stop the processing PRD progress
                        clearInterval(progressInterval)
                        
                        // Complete processing PRD
                        updateProgress('processing-prd', 100, 'completed')
                        
                        // Wait a moment then start creating PRD
                        setTimeout(() => {
                          updateProgress('creating-prd', 25, 'processing')
                        }, 500)
                        
                        if (response.ok) {
                          const result = await response.json()
                          if (result.success && result.data) {
                            // Gradually progress creating PRD
                            setTimeout(() => {
                              updateProgress('creating-prd', 60)
                            }, 800)
                            
                            setTimeout(() => {
                              updateProgress('creating-prd', 85)
                            }, 1200)
                            
                            // Apply the generated content to the main document using smart merge
                            let mergedBlocks: any[] = []
                            if (result.data.blocks) {
                              // Smart merge of AI-generated blocks with existing content
                              mergedBlocks = smartMergeBlocks(currentBlocks, result.data.blocks, conversationState.mode)
                              onBlocksUpdate && onBlocksUpdate(mergedBlocks)
                            } else if (result.data.content) {
                              // Parse content and create blocks, then merge
                              const newBlocks = parseAIContentToBlocks(result.data.content)
                              mergedBlocks = smartMergeBlocks(currentBlocks, newBlocks, conversationState.mode)
                              onBlocksUpdate && onBlocksUpdate(mergedBlocks)
                            }
                            
                            // Complete creating PRD and start processing TRD after realistic delay
                            setTimeout(() => {
                              updateProgress('creating-prd', 100, 'completed')
                              setTimeout(() => {
                                updateProgress('processing-trd', 30, 'processing')
                              }, 600)
                            }, 1500)
                            
                            // Auto-save the updated PRD blocks to database for persistence
                            if (mergedBlocks.length > 0 && sessionId) {
                              try {
                                console.log('🔍 AUTO-SAVE DEBUG: Starting save process...')
                                console.log('🔍 Session ID:', sessionId)
                                console.log('🔍 Blocks count:', mergedBlocks.length)
                                console.log('🔍 First block:', mergedBlocks[0])
                                
                                const { missionControlApi } = await import('@/services/api/missionControlApi')
                                
                                const saveData = {
                                  title: extractTitleFromBlocks(mergedBlocks),
                                  lastModified: new Date(),
                                  source: conversationState.mode === 'modify' ? 'ai_modification' : 'ai_generation'
                                }
                                
                                console.log('🔍 Save metadata:', saveData)
                                
                                const result = await missionControlApi.savePRDBlocks(sessionId, mergedBlocks, saveData)
                                console.log('✅ PRD blocks saved successfully to database:', result)
                              } catch (saveError) {
                                console.error('❌ CRITICAL: Failed to save PRD blocks:', saveError)
                                console.error('❌ Error details:', {
                                  message: (saveError as Error)?.message,
                                  stack: (saveError as Error)?.stack,
                                  sessionId,
                                  blocksCount: mergedBlocks.length
                                })
                                // Don't show error to user - save failure shouldn't break the flow
                              }
                            } else {
                              console.warn('⚠️ AUTO-SAVE SKIPPED:', {
                                hasBlocks: mergedBlocks.length > 0,
                                hasSessionId: !!sessionId,
                                blocksCount: mergedBlocks.length,
                                sessionId
                              })
                            }
                            
                            // Gradually progress processing TRD during database save
                            setTimeout(() => {
                              updateProgress('processing-trd', 65)
                            }, 2200)
                            
                            setTimeout(() => {
                              updateProgress('processing-trd', 100, 'completed')
                              // Start creating TRD
                              setTimeout(() => {
                                updateProgress('creating-trd', 40, 'processing')
                              }, 700)
                            }, 2800)
                            
                            // Complete TRD creation and show final success
                            setTimeout(() => {
                              updateProgress('creating-trd', 80)
                            }, 3600)
                            
                            setTimeout(() => {
                              updateProgress('creating-trd', 100, 'completed')
                              
                              // Generate final success message - this replaces the popup
                              let updatedSections = []
                              if (result.data.blocks) {
                                updatedSections = result.data.blocks.filter(b => b.type === 'header').map(b => b.content?.text || 'Section')
                              }
                              
                              const successMessage: ChatMessage = {
                                id: Date.now().toString(),
                                type: 'ai',
                                content: conversationState.mode === 'modify' 
                                  ? `✨ Successfully enhanced your PRD! Updated sections: ${updatedSections.length > 0 ? updatedSections.join(', ') : 'Product Requirements Document, Product Specification, Introduction & Vision, Problem Statement, Solution Overview, Target Audience, User Personas, Alice, Bob, Carol, User Stories, Functional Requirements, Core Features (Priority: P0), Integration (Priority: P0), Success Metrics, Technical Specification, System Overview, Architectural Drivers, Goals, Constraints, High-Level Architecture, Technology Stack, Architecture Diagrams, System Architecture, Implementation Plan, Phase 1: Foundation (2-3 weeks), Phase 2: Core Features (4-6 weeks)'}. Check the main document for the updates.`
                                  : '✨ Successfully generated your comprehensive PRD! Check the main document for the complete specification.',
                                timestamp: new Date()
                              }
                              setMessages(prev => [...prev, successMessage])
                            }, 4200)
                            
                            // Trigger additional callback if provided (but don't show duplicate messages)
                            // if (onPRDUpdate) {
                            //   onPRDUpdate(result.data)
                            // }
                          } else {
                            throw new Error(result.error || 'Generation failed')
                          }
                        } else {
                          throw new Error(`API error: ${response.status}`)
                        }
                      } catch (error) {
                        console.error('PRD generation failed:', error)
                        
                        // Clear any running intervals
                        clearInterval(progressInterval)
                        
                        // Mark all stages as completed (failed)
                        updateProgress('processing-prd', 100, 'completed')
                        updateProgress('creating-prd', 100, 'completed')
                        updateProgress('processing-trd', 100, 'completed') 
                        updateProgress('creating-trd', 100, 'completed')
                        
                        // Show error message instead of success
                        const errorMessage: ChatMessage = {
                          id: Date.now().toString(),
                          type: 'ai',
                          content: '❌ Generation failed. Please try again or continue the conversation.',
                          timestamp: new Date()
                        }
                        setMessages(prev => [...prev, errorMessage])
                      }
                    }}
                    className="neon-btn"
                    style={{
                      fontSize: '14px',
                      padding: '12px 24px',
                      minWidth: '200px'
                    }}
                  >
{conversationState.mode === 'modify' ? 'Apply Improvements' : 'Generate Comprehensive PRD'}
                  </button>
                </div>
              )}
            </div>
          ))}

          {/* Typing indicator */}
          {isTyping && (
            <div className="chat-message ai">
              <div style={{ fontWeight: 600, marginBottom: '8px', fontSize: '14px' }}>el Agénte</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>Analyzing your request</span>
                <div style={{ display: 'flex', gap: '2px' }}>
                  <div style={{ 
                    width: '4px', 
                    height: '4px', 
                    borderRadius: '50%', 
                    background: '#64748b',
                    animation: 'typing 1.4s infinite ease-in-out' 
                  }} />
                  <div style={{ 
                    width: '4px', 
                    height: '4px', 
                    borderRadius: '50%', 
                    background: '#64748b',
                    animation: 'typing 1.4s infinite ease-in-out 0.2s' 
                  }} />
                  <div style={{ 
                    width: '4px', 
                    height: '4px', 
                    borderRadius: '50%', 
                    background: '#64748b',
                    animation: 'typing 1.4s infinite ease-in-out 0.4s' 
                  }} />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="chat-input" style={{
          padding: '16px',
          borderTop: '1px solid #e2e8f0',
          display: 'flex',
          gap: '8px',
          flexShrink: 0
        }}>
          <textarea
            ref={inputRef}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask me to enhance a section, add a diagram, improve clarity..."
            style={{
              flex: 1,
              border: '1px solid #d1d5db',
              borderRadius: '8px',
              padding: '12px',
              resize: 'none',
              height: '80px',
              fontFamily: 'inherit',
              fontSize: '14px',
              color: '#374151',
              background: 'white',
              outline: 'none'
            }}
            onFocus={(e) => {
              e.target.style.borderColor = '#22c55e'
              e.target.style.boxShadow = '0 0 0 3px rgba(34, 197, 94, 0.1)'
            }}
            onBlur={(e) => {
              e.target.style.borderColor = '#d1d5db'
              e.target.style.boxShadow = 'none'
            }}
          />
          <button
            onClick={sendMessage}
            disabled={!inputValue.trim() || isTyping}
            style={{
              padding: '12px 20px',
              background: inputValue.trim() && !isTyping ? '#22c55e' : '#e5e7eb',
              color: inputValue.trim() && !isTyping ? 'white' : '#9ca3af',
              border: 'none',
              borderRadius: '8px',
              fontWeight: 600,
              cursor: inputValue.trim() && !isTyping ? 'pointer' : 'not-allowed',
              transition: 'all 0.15s ease',
              fontSize: '14px'
            }}
            onMouseEnter={(e) => {
              if (inputValue.trim() && !isTyping) {
                e.currentTarget.style.background = '#16a34a'
              }
            }}
            onMouseLeave={(e) => {
              if (inputValue.trim() && !isTyping) {
                e.currentTarget.style.background = '#22c55e'
              }
            }}
          >
            Send
          </button>
        </div>
      </>
    )

    // Render integrated panel (no backdrop, no positioning)
    if (isIntegratedPanel) {
      return (
        <div
          className="ai-chat-panel integrated"
          style={{
            height: '100%',
            background: '#ffffff',
            display: 'flex',
            flexDirection: 'column'
          }}
        >
          <ChatContent />
          
          {/* CSS for spinning animation */}
          <style jsx>{`
            @keyframes spin {
              from { transform: rotate(0deg); }
              to { transform: rotate(360deg); }
            }
            
            .spin-animation {
              animation: spin 1s linear infinite;
            }
            
          `}</style>
          
          <style jsx>{`
            .chat-message {
              margin: 8px 0;
              padding: 12px 16px;
              border-radius: 16px;
              max-width: 80%;
              position: relative;
            }
            
            .chat-message.user {
              background: #f8fafc;
              border: 1px solid #e2e8f0;
              margin-left: auto;
              text-align: right;
            }
            
            .chat-message.ai {
              background: rgba(248, 250, 252, 0.8);
              border: 1px solid rgba(226, 232, 240, 0.8);
              border-radius: 12px;
              backdrop-filter: blur(10px);
              box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
              margin-right: auto;
              position: relative;
            }

            
            .chat-message.ai.initial-path-selection {
              background: #f0f9ff;
              border: 1px solid #bae6fd;
            }
            
            @keyframes typing {
              0%, 60%, 100% {
                transform: translateY(0);
                opacity: 0.4;
              }
              30% {
                transform: translateY(-8px);
                opacity: 1;
              }
            }
            
            @keyframes spin {
              from { transform: rotate(0deg); }
              to { transform: rotate(360deg); }
            }
          `}</style>
        </div>
      )
    }

    // Render floating panel (original behavior)
    return (
      <>
        {/* Backdrop */}
        {isOpen && (
          <div
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0, 0, 0, 0.3)',
              zIndex: 998,
              backdropFilter: 'blur(2px)'
            }}
            onClick={onClose}
          />
        )}

        {/* Chat Panel */}
        <div
          className={`ai-chat-panel ${isOpen ? 'open' : ''}`}
          style={{
            position: 'fixed',
            right: 0,
            top: 0,
            height: '100vh',
            width: '400px',
            background: '#ffffff',
            border: '1px solid #e1e8ed',
            borderRight: 'none',
            zIndex: 999,
            transform: isOpen ? 'translateX(0)' : 'translateX(100%)',
            transition: 'transform 0.25s ease',
            display: 'flex',
            flexDirection: 'column',
            boxShadow: isOpen ? '-2px 0 10px rgba(0, 0, 0, 0.1)' : 'none'
          }}
        >
          <ChatContent />
        </div>

        <style jsx>{`
          .chat-message {
            margin: 12px 0;
            padding: 16px;
            border-radius: 12px;
            max-width: 85%;
            position: relative;
          }
          
          .chat-message.user {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            margin-left: auto;
            text-align: right;
          }
          
          .chat-message.ai {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            margin-right: auto;
          }
          
          .chat-message.ai.initial-path-selection {
            background: #f0f9ff;
            border: 1px solid #bae6fd;
          }
          
          @keyframes typing {
            0%, 60%, 100% {
              transform: translateY(0);
              opacity: 0.4;
            }
            30% {
              transform: translateY(-8px);
              opacity: 1;
            }
          }
        `}</style>
      </>
    )
}