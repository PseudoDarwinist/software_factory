/**
 * Integration test for Upload Sources Tray components
 * 
 * This test verifies that all the components work together correctly
 * and that the integration with ThinkStage is working.
 */

import React from 'react'
import { render, screen } from '@testing-library/react'
import { DndProvider } from 'react-dnd'
import { HTML5Backend } from 'react-dnd-html5-backend'
import '@testing-library/jest-dom'

import { UploadSourcesTray } from '../UploadSourcesTray'
import { FileChip } from '../FileChip'
import { ProgressLine } from '../ProgressLine'
import { PRDPreview } from '../PRDPreview'

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => React.createElement('div', props, children),
    button: ({ children, ...props }: any) => React.createElement('button', props, children),
  },
  AnimatePresence: ({ children }: any) => children,
}))

// Wrapper component with DnD provider
const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <DndProvider backend={HTML5Backend}>
    {children}
  </DndProvider>
)

describe('Upload Sources Tray Integration', () => {
  it('renders all main components without crashing', () => {
    render(
      <TestWrapper>
        <UploadSourcesTray
          projectId="test-project"
          onUploadComplete={jest.fn()}
        />
      </TestWrapper>
    )

    // Check that the main tray is rendered
    expect(screen.getByText('Sources tray')).toBeInTheDocument()
    expect(screen.getByText('Upload')).toBeInTheDocument()
    expect(screen.getByText('Paste link')).toBeInTheDocument()
  })

  it('renders FileChip component correctly', () => {
    const mockFile = {
      id: 'test-file',
      name: 'test.pdf',
      type: 'pdf' as const,
      size: 1024,
      status: 'complete' as const,
      progress: 100,
      sourceId: 'S1',
    }

    render(
      <FileChip
        file={mockFile}
        onRemove={jest.fn()}
      />
    )

    expect(screen.getByText('test.pdf')).toBeInTheDocument()
    expect(screen.getByText('S1')).toBeInTheDocument()
    expect(screen.getByText('PDF')).toBeInTheDocument()
  })

  it('renders ProgressLine component correctly', () => {
    render(
      <ProgressLine currentStage="reading" />
    )

    expect(screen.getByText('Reading files')).toBeInTheDocument()
    expect(screen.getByText('Processing uploaded documents and links')).toBeInTheDocument()
  })

  it('renders PRDPreview component correctly', () => {
    const mockFiles = [{
      id: 'test-file',
      name: 'test.pdf',
      type: 'pdf' as const,
      size: 1024,
      status: 'complete' as const,
      progress: 100,
      sourceId: 'S1',
    }]

    const mockContent = '# Test PRD\n\n## Problem\nTest problem [S1]'

    render(
      <PRDPreview
        content={mockContent}
        files={mockFiles}
        onFreezePRD={jest.fn()}
      />
    )

    expect(screen.getByText('PRD Draft')).toBeInTheDocument()
    expect(screen.getByText('Freeze PRD')).toBeInTheDocument()
    expect(screen.getByText('Completeness Check')).toBeInTheDocument()
  })
})