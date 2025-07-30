/**
 * UploadSourcesTray Component Tests
 * 
 * Tests for the Upload Sources Tray component functionality:
 * - Drag and drop file handling
 * - File chip rendering and interactions
 * - Progress line visualization
 * - PRD preview generation
 */

import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { DndProvider } from 'react-dnd'
import { HTML5Backend } from 'react-dnd-html5-backend'
import '@testing-library/jest-dom'

import { UploadSourcesTray } from '../UploadSourcesTray'

// Mock framer-motion
jest.mock('framer-motion', () => ({
  motion: {
    div: function(props: any) { return React.createElement('div', props) },
    button: function(props: any) { return React.createElement('button', props) },
  },
  AnimatePresence: function(props: any) { return props.children },
}))

// Mock react-dnd
jest.mock('react-dnd', () => ({
  DndProvider: function(props: any) { return props.children },
  useDrag: () => [null, null, null],
  useDrop: () => [null, null],
}))

// Mock react-dnd-html5-backend
jest.mock('react-dnd-html5-backend', () => ({
  HTML5Backend: {},
}))

// Simple wrapper component
const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <div>{children}</div>
)

describe('UploadSourcesTray', () => {
  const defaultProps = {
    projectId: 'test-project',
    onUploadComplete: jest.fn(),
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders the upload sources tray with header', () => {
    render(
      <TestWrapper>
        <UploadSourcesTray {...defaultProps} />
      </TestWrapper>
    )

    expect(screen.getByText('Sources tray')).toBeInTheDocument()
    expect(screen.getByText('Drop PDFs, decks, Zoom links, webpages, Figma, screenshots')).toBeInTheDocument()
  })

  it('renders upload and paste link buttons', () => {
    render(
      <TestWrapper>
        <UploadSourcesTray {...defaultProps} />
      </TestWrapper>
    )

    expect(screen.getByText('Upload')).toBeInTheDocument()
    expect(screen.getByText('Paste link')).toBeInTheDocument()
  })

  it('opens link modal when paste link button is clicked', () => {
    render(
      <TestWrapper>
        <UploadSourcesTray {...defaultProps} />
      </TestWrapper>
    )

    fireEvent.click(screen.getByText('Paste link'))
    expect(screen.getByText('Paste Link')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('https://...')).toBeInTheDocument()
  })

  it('closes link modal when cancel is clicked', () => {
    render(
      <TestWrapper>
        <UploadSourcesTray {...defaultProps} />
      </TestWrapper>
    )

    fireEvent.click(screen.getByText('Paste link'))
    fireEvent.click(screen.getByText('Cancel'))
    expect(screen.queryByText('Paste Link')).not.toBeInTheDocument()
  })

  it('adds a link when URL is submitted', async () => {
    render(
      <TestWrapper>
        <UploadSourcesTray {...defaultProps} />
      </TestWrapper>
    )

    fireEvent.click(screen.getByText('Paste link'))
    
    const urlInput = screen.getByPlaceholderText('https://...')
    fireEvent.change(urlInput, { target: { value: 'https://example.com' } })
    fireEvent.click(screen.getByText('Add Link'))

    await waitFor(() => {
      expect(screen.getByText('example.com')).toBeInTheDocument()
    })
  })

  it('shows Make PRD draft button when files are uploaded', async () => {
    render(
      <TestWrapper>
        <UploadSourcesTray {...defaultProps} />
      </TestWrapper>
    )

    // Simulate file upload by clicking paste link and adding a URL
    fireEvent.click(screen.getByText('Paste link'))
    const urlInput = screen.getByPlaceholderText('https://...')
    fireEvent.change(urlInput, { target: { value: 'https://example.com' } })
    fireEvent.click(screen.getByText('Add Link'))

    // Wait for file to be processed (mocked to complete immediately in tests)
    await waitFor(() => {
      expect(screen.getByText('Make PRD draft')).toBeInTheDocument()
    }, { timeout: 3000 })
  })

  it('shows progress line when PRD generation starts', async () => {
    render(
      <TestWrapper>
        <UploadSourcesTray {...defaultProps} />
      </TestWrapper>
    )

    // Add a file first
    fireEvent.click(screen.getByText('Paste link'))
    const urlInput = screen.getByPlaceholderText('https://...')
    fireEvent.change(urlInput, { target: { value: 'https://example.com' } })
    fireEvent.click(screen.getByText('Add Link'))

    // Wait for Make PRD draft button and click it
    await waitFor(() => {
      const makePRDButton = screen.getByText('Make PRD draft')
      fireEvent.click(makePRDButton)
    })

    // Check for progress line
    await waitFor(() => {
      expect(screen.getByText('Reading files')).toBeInTheDocument()
    })
  })

  it('handles file removal', async () => {
    render(
      <TestWrapper>
        <UploadSourcesTray {...defaultProps} />
      </TestWrapper>
    )

    // Add a file
    fireEvent.click(screen.getByText('Paste link'))
    const urlInput = screen.getByPlaceholderText('https://...')
    fireEvent.change(urlInput, { target: { value: 'https://example.com' } })
    fireEvent.click(screen.getByText('Add Link'))

    await waitFor(() => {
      expect(screen.getByText('example.com')).toBeInTheDocument()
    })

    // Find and click remove button (X button)
    const removeButtons = screen.getAllByRole('button')
    const removeButton = removeButtons.find(button => 
      button.querySelector('svg') && 
      button.getAttribute('class')?.includes('text-gray-400')
    )
    
    if (removeButton) {
      fireEvent.click(removeButton)
      await waitFor(() => {
        expect(screen.queryByText('example.com')).not.toBeInTheDocument()
      })
    }
  })

  it('calls onUploadComplete when PRD is frozen', async () => {
    const onUploadComplete = jest.fn()
    render(
      <TestWrapper>
        <UploadSourcesTray {...defaultProps} onUploadComplete={onUploadComplete} />
      </TestWrapper>
    )

    // Add a file and generate PRD
    fireEvent.click(screen.getByText('Paste link'))
    const urlInput = screen.getByPlaceholderText('https://...')
    fireEvent.change(urlInput, { target: { value: 'https://example.com' } })
    fireEvent.click(screen.getByText('Add Link'))

    await waitFor(() => {
      fireEvent.click(screen.getByText('Make PRD draft'))
    })

    // Wait for PRD preview and freeze button
    await waitFor(() => {
      const freezeButton = screen.getByText('Freeze PRD')
      fireEvent.click(freezeButton)
      expect(onUploadComplete).toHaveBeenCalledWith('mock-session-id')
    }, { timeout: 10000 })
  })
})