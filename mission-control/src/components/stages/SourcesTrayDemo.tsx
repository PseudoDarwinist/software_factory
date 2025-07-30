/**
 * Demo page for SourcesTrayCard component
 * Shows different states and interactions
 */

import React, { useState } from 'react'
import { SourcesTrayCard } from './SourcesTrayCard'

interface FileItem {
  name: string
  type: 'pdf' | 'video' | 'image' | 'document' | 'link'
  progress: number
  error?: string
}

export const SourcesTrayDemo: React.FC = () => {
  const [status, setStatus] = useState<'idle' | 'uploading' | 'analyzing' | 'drafting' | 'ready'>('ready')
  const [files, setFiles] = useState<FileItem[]>([
    { name: 'user_research.pdf', type: 'pdf', progress: 1 },
    { name: 'market_analysis.pdf', type: 'pdf', progress: 1 },
    { name: 'competitor_research.pdf', type: 'pdf', progress: 1 }
  ])

  const handleFileAdd = (newFiles: File[]) => {
    const fileItems: FileItem[] = newFiles.map(file => ({
      name: file.name,
      type: file.name.endsWith('.pdf') ? 'pdf' : 
            file.name.endsWith('.mp4') || file.name.endsWith('.mov') ? 'video' : 'document',
      progress: 0
    }))
    
    setFiles(prev => [...prev, ...fileItems])
    setStatus('uploading')
    
    // Simulate upload progress
    fileItems.forEach((_, index) => {
      setTimeout(() => {
        setFiles(prev => prev.map((file, i) => 
          i >= prev.length - fileItems.length + index ? { ...file, progress: 1 } : file
        ))
      }, 1000 + index * 500)
    })
  }

  const handleLinkAdd = (url: string) => {
    const domain = new URL(url).hostname.replace('www.', '')
    const newFile: FileItem = {
      name: domain,
      type: 'link',
      progress: 0
    }
    
    setFiles(prev => [...prev, newFile])
    setStatus('uploading')
    
    // Simulate processing
    setTimeout(() => {
      setFiles(prev => prev.map(file => 
        file.name === domain ? { ...file, progress: 1 } : file
      ))
    }, 1500)
  }

  const handleFileRemove = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleAnalyze = () => {
    setStatus('analyzing')
    setTimeout(() => setStatus('drafting'), 2000)
    setTimeout(() => setStatus('ready'), 4000)
  }

  const handleFreezePRD = () => {
    alert('PRD Frozen! 🎉')
  }

  return (
    <div 
      className="min-h-screen p-8"
      style={{ background: '#0A0E12' }}
    >
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-white mb-4">Sources Tray Card Demo</h1>
          
          {/* Status Controls */}
          <div className="flex gap-2 mb-4">
            {(['idle', 'uploading', 'analyzing', 'drafting', 'ready'] as const).map(s => (
              <button
                key={s}
                onClick={() => setStatus(s)}
                className={`px-3 py-1 rounded text-sm ${
                  status === s 
                    ? 'bg-blue-600 text-white' 
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                }`}
              >
                {s}
              </button>
            ))}
          </div>
          
          <div className="text-gray-400 text-sm">
            Current status: <span className="text-blue-400 font-mono">{status}</span>
          </div>
        </div>

        <SourcesTrayCard
          status={status}
          files={files}
          onFileAdd={handleFileAdd}
          onLinkAdd={handleLinkAdd}
          onFileRemove={handleFileRemove}
          onAnalyze={handleAnalyze}
          onFreezePRD={handleFreezePRD}
        />
        
        <div className="mt-8 text-gray-400 text-sm">
          <p><strong>✨ NEW: 6-Section PRD Summary</strong></p>
          <p>• Set status to "ready" to see the structured PRD summary with source attribution</p>
          <p>• Hover over [S1], [S2], [S3] tags to see source tooltips</p>
          <p>• Try different statuses to see the improved 6-section placeholder</p>
          <p>• The component shows: Problem, Audience, Goals, Risks, Competitive scan, Open questions</p>
          <p>• Try dragging files onto the drop zone or clicking + buttons</p>
        </div>
      </div>
    </div>
  )
}