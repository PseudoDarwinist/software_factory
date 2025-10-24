import React from 'react'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import '@testing-library/jest-dom'
import { DiagramBlock } from '../DiagramBlock'
import type { Block } from '@/lib/blocks/types'

// Mock mermaid module
jest.mock('mermaid', () => ({
  default: {
    initialize: jest.fn(),
    render: jest.fn().mockResolvedValue({ svg: '<svg>test diagram</svg>' })
  }
}))

describe('DiagramBlock', () => {
  const mockBlock: Block = {
    id: 'test-block-1',
    type: 'mermaid-diagram',
    content: {
      code: 'flowchart LR\n  A --> B',
      diagramType: 'flowchart'
    },
    position: 0,
    createdAt: new Date(),
    updatedAt: new Date()
  }

  const mockOnUpdate = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  test('renders diagram in display mode', async () => {
    render(<DiagramBlock block={mockBlock} onUpdate={mockOnUpdate} />)
    
    expect(screen.getByText(/Mermaid • flowchart/)).toBeInTheDocument()
    expect(screen.getByText('Click to edit')).toBeInTheDocument()
  })

  test('enters edit mode when clicked', async () => {
    render(<DiagramBlock block={mockBlock} onUpdate={mockOnUpdate} />)
    
    const container = screen.getByText(/Mermaid/).closest('div')
    
    await act(async () => {
      fireEvent.click(container!)
    })
    
    await waitFor(() => {
      expect(screen.getByText(/Edit Mermaid Diagram/)).toBeInTheDocument()
      expect(screen.getByText('Update Diagram')).toBeInTheDocument()
      expect(screen.getByText('Cancel')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('Enter Mermaid diagram code...')).toBeInTheDocument()
    })
  })

  test('shows code editor and preview in edit mode', async () => {
    render(<DiagramBlock block={mockBlock} onUpdate={mockOnUpdate} />)
    
    const container = screen.getByText(/Mermaid/).closest('div')
    
    await act(async () => {
      fireEvent.click(container!)
    })
    
    await waitFor(() => {
      expect(screen.getByText('Code')).toBeInTheDocument()
      expect(screen.getByText('Preview')).toBeInTheDocument()
      
      const textarea = screen.getByPlaceholderText('Enter Mermaid diagram code...')
      expect(textarea).toHaveValue('flowchart LR\n  A --> B')
    })
  })

  test('updates diagram code when Update Diagram is clicked', async () => {
    render(<DiagramBlock block={mockBlock} onUpdate={mockOnUpdate} />)
    
    const container = screen.getByText(/Mermaid/).closest('div')
    
    await act(async () => {
      fireEvent.click(container!)
    })
    
    await waitFor(() => {
      const textarea = screen.getByPlaceholderText('Enter Mermaid diagram code...')
      fireEvent.change(textarea, { target: { value: 'flowchart TD\n  A --> C' } })
    })
    
    const updateButton = screen.getByText('Update Diagram')
    
    await act(async () => {
      fireEvent.click(updateButton)
    })
    
    expect(mockOnUpdate).toHaveBeenCalledWith({
      ...mockBlock,
      content: {
        ...mockBlock.content,
        code: 'flowchart TD\n  A --> C'
      }
    })
  })

  test('cancels editing when Cancel is clicked', async () => {
    render(<DiagramBlock block={mockBlock} onUpdate={mockOnUpdate} />)
    
    const container = screen.getByText(/Mermaid/).closest('div')
    
    await act(async () => {
      fireEvent.click(container!)
    })
    
    await waitFor(() => {
      const textarea = screen.getByPlaceholderText('Enter Mermaid diagram code...')
      fireEvent.change(textarea, { target: { value: 'modified code' } })
    })
    
    const cancelButton = screen.getByText('Cancel')
    
    await act(async () => {
      fireEvent.click(cancelButton)
    })
    
    await waitFor(() => {
      expect(screen.getByText(/Mermaid/)).toBeInTheDocument()
      expect(screen.queryByText(/Edit Mermaid Diagram/)).not.toBeInTheDocument()
    })
    
    expect(mockOnUpdate).not.toHaveBeenCalled()
  })

  test('handles Tab key for indentation in code editor', async () => {
    render(<DiagramBlock block={mockBlock} onUpdate={mockOnUpdate} />)
    
    const container = screen.getByText(/Mermaid/).closest('div')
    
    await act(async () => {
      fireEvent.click(container!)
    })
    
    await waitFor(() => {
      const textarea = screen.getByPlaceholderText('Enter Mermaid diagram code...') as HTMLTextAreaElement
      
      // Set cursor position and fire Tab key
      textarea.selectionStart = 0
      textarea.selectionEnd = 0
      
      act(() => {
        fireEvent.keyDown(textarea, { key: 'Tab' })
      })
      
      expect(textarea.value).toBe('  flowchart LR\n  A --> B')
    })
  })

  test('displays error when diagram rendering fails', async () => {
    const mermaid = require('mermaid')
    mermaid.default.render.mockRejectedValueOnce(new Error('Invalid syntax'))
    
    const blockWithError = {
      ...mockBlock,
      content: { code: 'invalid mermaid code', diagramType: 'flowchart' }
    }
    
    render(<DiagramBlock block={blockWithError} onUpdate={mockOnUpdate} />)
    
    await waitFor(() => {
      expect(screen.getByText(/Diagram error: Invalid syntax/)).toBeInTheDocument()
      expect(screen.getByText('invalid mermaid code')).toBeInTheDocument()
    })
  })

  test('shows preview error in edit mode with invalid syntax', async () => {
    const mermaid = require('mermaid')
    mermaid.default.render.mockRejectedValueOnce(new Error('Preview error'))
    
    render(<DiagramBlock block={mockBlock} onUpdate={mockOnUpdate} />)
    
    const container = screen.getByText(/Mermaid/).closest('div')
    
    await act(async () => {
      fireEvent.click(container!)
    })
    
    await waitFor(() => {
      const textarea = screen.getByPlaceholderText('Enter Mermaid diagram code...')
      
      act(() => {
        fireEvent.change(textarea, { target: { value: 'invalid syntax' } })
      })
    })
    
    // Wait for debounced preview rendering
    await waitFor(() => {
      expect(screen.getByText(/Preview error: Preview error/)).toBeInTheDocument()
    }, { timeout: 1000 })
  })

  test('shows placeholder when no code in preview', async () => {
    render(<DiagramBlock block={mockBlock} onUpdate={mockOnUpdate} />)
    
    const container = screen.getByText(/Mermaid/).closest('div')
    
    await act(async () => {
      fireEvent.click(container!)
    })
    
    await waitFor(() => {
      const textarea = screen.getByPlaceholderText('Enter Mermaid diagram code...')
      
      act(() => {
        fireEvent.change(textarea, { target: { value: '' } })
      })
    })
    
    expect(screen.getByText('Enter code to see preview...')).toBeInTheDocument()
  })
})