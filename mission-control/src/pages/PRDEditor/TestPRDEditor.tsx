import React, { useState } from 'react'
import { Block } from '@/lib/blocks/types'
import { BlockRenderer } from '@/components/prd/BlockRenderer'
import { SidebarTOC } from '@/components/prd/SidebarTOC'
import { FloatingChatButton } from '@/components/prd/FloatingChatButton'
import { AIChatPanel } from '@/components/prd/AIChatPanel'

// Sample test blocks to demonstrate the editor
const testBlocks: Block[] = [
  {
    id: 'header-1',
    type: 'header',
    content: { level: 1, text: 'Product Requirements Document' }
  },
  {
    id: 'para-1',
    type: 'paragraph',
    content: { text: 'This is a test PRD to demonstrate the new block-based editor with Notion-like functionality.' }
  },
  {
    id: 'header-2',
    type: 'header',
    content: { level: 2, text: 'Problem Statement' }
  },
  {
    id: 'para-2',
    type: 'paragraph',
    content: { text: 'The current system lacks an intuitive block-based editing experience that allows users to easily create and modify PRD content with inline editing capabilities.' }
  },
  {
    id: 'header-3',
    type: 'header',
    content: { level: 2, text: 'Solution Overview' }
  },
  {
    id: 'para-3',
    type: 'paragraph',
    content: { text: 'We have implemented a comprehensive block-based editor with the following features:' }
  },
  {
    id: 'list-1',
    type: 'bullet-list',
    content: { 
      items: [
        'Inline editing for headers and paragraphs',
        'Sidebar table of contents with scroll sync',
        'Hover controls for block management',
        'Real-time persistence to backend API',
        'Notion-like styling and interactions'
      ]
    }
  },
  {
    id: 'header-4',
    type: 'header',
    content: { level: 2, text: 'Technical Implementation' }
  },
  {
    id: 'para-4',
    type: 'paragraph',
    content: { text: 'The editor enforces a block contract by default and supports various block types including headers, paragraphs, lists, code blocks, and Mermaid diagrams.' }
  },
  {
    id: 'code-1',
    type: 'code',
    content: { 
      language: 'typescript',
      code: 'interface Block {\n  id: string\n  type: string\n  content: any\n}'
    }
  },
  {
    id: 'header-5',
    type: 'header',
    content: { level: 2, text: 'Architecture Diagram' }
  },
  {
    id: 'diagram-1',
    type: 'mermaid-diagram',
    content: {
      code: 'flowchart TD\n    A[User Input] --> B[Block Editor]\n    B --> C[Block Renderer]\n    C --> D[API Persistence]\n    D --> E[Database]\n    C --> F[Sidebar TOC]\n    F --> G[Scroll Sync]'
    }
  }
]

export const TestPRDEditor: React.FC = () => {
  return (
    <div style={{ minHeight: '100vh', background: '#0b0f18', color: 'white' }}>
      <header style={{ 
        position: 'sticky', 
        top: 0, 
        zIndex: 10, 
        backdropFilter: 'blur(10px)', 
        background: 'rgba(12,16,24,0.6)', 
        borderBottom: '1px solid rgba(255,255,255,0.06)' 
      }}>
        <div style={{ maxWidth: 1200, margin: '0 auto', padding: '1rem' }}>
          <h1 style={{ margin: 0, fontSize: 18, letterSpacing: 0.2 }}>PRD Editor Test - Block-based with Notion-like Interface</h1>
          <div style={{ fontSize: 12, opacity: 0.65 }}>
            Test all the implemented features: inline editing, sidebar TOC, block controls
          </div>
        </div>
      </header>
      
      <div style={{ 
        maxWidth: 1200, 
        margin: '0 auto', 
        display: 'flex', 
        gap: '2rem', 
        padding: '1rem', 
        minHeight: 'calc(100vh - 100px)' 
      }}>
        {/* Sidebar */}
        <aside style={{ width: 280, flexShrink: 0 }}>
          <SidebarTOC blocks={testBlocks} />
        </aside>
        
        {/* Main content */}
        <main style={{ flex: 1, minWidth: 0 }}>
          <div style={{ 
            background: 'rgba(255, 255, 255, 0.02)', 
            border: '1px solid rgba(255, 255, 255, 0.08)', 
            borderRadius: '12px',
            padding: '2rem',
            marginBottom: '1rem'
          }}>
            <div style={{ color: '#15F1CC', fontSize: '14px', marginBottom: '1rem' }}>
              ✨ <strong>Features to test:</strong>
            </div>
            <ul style={{ color: '#8EA3B5', fontSize: '14px', lineHeight: 1.6 }}>
              <li>Click on any header or paragraph to edit inline</li>
              <li>Hover over blocks to see control buttons</li>
              <li>Use the sidebar to navigate between sections</li>
              <li>Try the block type selector in hover controls</li>
              <li>Press Enter to save, Escape to cancel editing</li>
            </ul>
          </div>
          
          <BlockRenderer 
            blocks={testBlocks}
            sessionId="test-session"
            onBlocksChange={(updatedBlocks) => {
              console.log('Blocks updated:', updatedBlocks)
            }}
          />
        </main>
      </div>
    </div>
  )
}

export default TestPRDEditor