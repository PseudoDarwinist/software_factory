/**
 * BuildStage - Monitor & Review Dashboard for Task Execution
 * 
 * This component implements the Build stage dashboard showing:
 * - Left sidebar with Running, Review, Failed task categories
 * - Main content area with detailed task information and live logs
 * - Right sidebar with diff preview and PR management
 * - Real-time progress updates via WebSocket
 * - Task approval/retry workflows
 * 
 * Requirements addressed:
 * - Requirement 5: Build agent monitoring and PR management
 * - Requirement 19: Build stage monitoring with agent chain visualization
 */

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { io, Socket } from 'socket.io-client'
import { LiquidCard } from '@/components/core/LiquidCard'
import missionControlApi from '@/services/api/missionControlApi'
import type { Task } from '@/types'
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels"

interface BuildStageProps {
  selectedProject: string | null
  onStageChange?: (stage: string) => void
}

export const BuildStage: React.FC<BuildStageProps> = ({
  selectedProject,
  onStageChange
}) => {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [socket, setSocket] = useState<Socket | null>(null)
  const [prDiff, setPrDiff] = useState<string | null>(null)
  
  // Ref for auto-scrolling live log
  const logContainerRef = useRef<HTMLDivElement>(null)

  // Fetch tasks from API
  const fetchTasks = useCallback(async () => {
    if (!selectedProject) return

    try {
      setLoading(true)
      setError(null)
      
      const tasksData = await missionControlApi.getTasks(selectedProject)
      // Filter to only show tasks that are in build-related states
      const buildTasks = tasksData.filter(task => 
        ['running', 'review', 'failed'].includes(task.status)
      )
      setTasks(buildTasks)
      
      // Auto-select first task if none selected
      if (!selectedTask && buildTasks.length > 0) {
        setSelectedTask(buildTasks[0])
      }
    } catch (err) {
      console.error('Error fetching tasks:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch tasks')
    } finally {
      setLoading(false)
    }
  }, [selectedProject, selectedTask])

  // Load initial tasks
  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  // WebSocket connection for real-time updates
  useEffect(() => {
    const newSocket = io('http://localhost:8000')
    setSocket(newSocket)

    newSocket.on('connect', () => {
      console.log('Build stage WebSocket connected:', newSocket.id)
    })

    newSocket.on('task_progress', (updatedTask: Task) => {
      console.log('Received task update:', updatedTask)

      // Update tasks list efficiently
      setTasks(prev => {
        const idx = prev.findIndex(t => t.id === updatedTask.id)
        if (idx === -1) return prev
        const next = [...prev]
        next[idx] = updatedTask
        return next
      })

      // Always keep selectedTask in sync using functional form so we don’t rely on
      // stale closures.
      setSelectedTask(prev => (prev && prev.id === updatedTask.id ? updatedTask : prev))
    })

    newSocket.on('disconnect', () => {
      console.log('Build stage WebSocket disconnected')
    })

    return () => {
      newSocket.disconnect()
    }
  }, [selectedTask])

  // Subscribe to the selected task to receive its live progress log
  useEffect(() => {
    if (!socket) return

    if (selectedTask) {
      console.log(`Subscribing to build task ${selectedTask.id}`)
      socket.emit('subscribe_task', { taskId: selectedTask.id })

      return () => {
        console.log(`Unsubscribing from build task ${selectedTask.id}`)
        socket.emit('unsubscribe_task', { taskId: selectedTask.id })
      }
    }
  }, [socket, selectedTask])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (logContainerRef.current && selectedTask?.progressMessages) {
      const container = logContainerRef.current
      container.scrollTop = container.scrollHeight
    }
  }, [selectedTask?.progressMessages])

  // Group tasks by status
  const tasksByStatus = useMemo(() => {
    const grouped = {
      running: [] as Task[],
      review: [] as Task[],
      failed: [] as Task[]
    }

    tasks.forEach(task => {
      if (grouped[task.status as keyof typeof grouped]) {
        grouped[task.status as keyof typeof grouped].push(task)
      }
    })

    return grouped
  }, [tasks])

  // Handle task selection
  const handleTaskSelect = useCallback(async (task: Task) => {
    setSelectedTask(task)
    
    // Load PR diff if task has PR URL
    if (task.pr_url) {
      try {
        // Mock PR diff for now - in real implementation would fetch from GitHub API
        setPrDiff(`--- a/ui/theme/tokens.css
+++ b/ui/theme/tokens.css
@@ -100,6 +100,10 @@
   text-100: #FFFFFF;
+  text-200: #F0F0F0;
+  
+  bg-900: #0A0A10;
+  bg-800: #1A1A20;`)
      } catch (err) {
        console.error('Error loading PR diff:', err)
        setPrDiff(null)
      }
    } else {
      setPrDiff(null)
    }
  }, [])

  // Handle task approval
  const handleApproveTask = useCallback(async (taskId: string) => {
    try {
      console.log('Approving task:', taskId)
      await missionControlApi.approveTask(taskId, 'user')
      await fetchTasks() // Refresh tasks
    } catch (err) {
      console.error('Error approving task:', err)
    }
  }, [fetchTasks])

  // Handle task retry
  const handleRetryTask = useCallback(async (taskId: string) => {
    try {
      const task = tasks.find(t => t.id === taskId)
      if (task && task.agent) {
        await missionControlApi.retryTask(taskId, task.agent)
        await fetchTasks() // Refresh tasks
      }
    } catch (err) {
      console.error('Error retrying task:', err)
    }
  }, [tasks, fetchTasks])

  // Get task chain status
  const getTaskChain = useCallback((task: Task) => {
    // Mock agent chain - in real implementation would come from task data
    const chains = {
      'feature-builder': ['feature-builder', 'test-runner', 'code-reviewer'],
      'test-runner': ['test-runner', 'code-reviewer'],
      'debugger': ['debugger'],
      'code-reviewer': ['code-reviewer']
    }
    
    return chains[task.agent as keyof typeof chains] || ['feature-builder']
  }, [])

  // Get elapsed time for running tasks
  const getElapsedTime = useCallback((task: Task) => {
    if (!task.started_at) return '0m'
    
    const start = new Date(task.started_at)
    const now = new Date()
    const diffMs = now.getTime() - start.getTime()
    const diffMins = Math.floor(diffMs / (1000 * 60))
    
    if (diffMins < 60) {
      return `${diffMins}m`
    } else {
      const hours = Math.floor(diffMins / 60)
      const mins = diffMins % 60
      return `${hours}h ${mins}m`
    }
  }, [])

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-white/60">Loading build tasks...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-400 mb-4">{error}</p>
          <button
            onClick={fetchTasks}
            className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg text-white transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full bg-gray-900 text-white">
      <PanelGroup direction="horizontal">
        {/* Left Sidebar - Task Categories */}
        <Panel defaultSize={25} minSize={20} maxSize={40}>
          <div className="h-full bg-gray-800/50 border-r border-white/10 flex flex-col">
            <div className="p-6 border-b border-white/10">
              <h1 className="text-2xl font-bold text-yellow-400 mb-2">Build • Monitor & Review</h1>
            </div>
            
            <div className="flex-1 overflow-y-auto">
              {/* Running Tasks */}
              <TaskCategory
                title="Running"
                tasks={tasksByStatus.running}
                selectedTask={selectedTask}
                onTaskSelect={handleTaskSelect}
                getElapsedTime={getElapsedTime}
                getTaskChain={getTaskChain}
              />
              
              {/* Review Tasks */}
              <TaskCategory
                title="Review"
                tasks={tasksByStatus.review}
                selectedTask={selectedTask}
                onTaskSelect={handleTaskSelect}
                getElapsedTime={getElapsedTime}
                getTaskChain={getTaskChain}
              />
              
              {/* Failed Tasks */}
              <TaskCategory
                title="Failed"
                tasks={tasksByStatus.failed}
                selectedTask={selectedTask}
                onTaskSelect={handleTaskSelect}
                getElapsedTime={getElapsedTime}
                getTaskChain={getTaskChain}
              />
            </div>
          </div>
        </Panel>

        <PanelResizeHandle className="w-1 bg-white/10 hover:bg-purple-500/50 cursor-col-resize transition-colors relative group">
          <div className="absolute inset-y-0 -left-1 -right-1 group-hover:bg-purple-500/20" />
        </PanelResizeHandle>

        {/* Main Content Area */}
        <Panel defaultSize={50} minSize={30}>
          <div className="h-full flex flex-col">
            {selectedTask ? (
              <>
                {/* Task Header */}
                <div className="p-6 border-b border-white/10">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-xl font-semibold text-yellow-400 mb-1">
                        {selectedTask.task_number} • {selectedTask.title}
                      </h2>
                      <div className="flex items-center space-x-4 text-sm text-white/60">
                        <span>Chain: {getTaskChain(selectedTask).join(' → ')}</span>
                        {selectedTask.started_at && (
                          <span>Started: {getElapsedTime(selectedTask)} ago</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className={clsx(
                        'px-3 py-1 rounded-full text-xs font-medium',
                        selectedTask.status === 'running' && 'bg-blue-500/20 text-blue-300',
                        selectedTask.status === 'review' && 'bg-yellow-500/20 text-yellow-300',
                        selectedTask.status === 'failed' && 'bg-red-500/20 text-red-300'
                      )}>
                        {selectedTask.status.toUpperCase()}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Live Log */}
                <div className="flex-1 p-6 flex flex-col min-h-0">
                  <div className="mb-4">
                    <h3 className="text-lg font-medium text-yellow-400 mb-2">Live log</h3>
                  </div>
                  
                  <div 
                    ref={logContainerRef}
                    className="bg-black/50 rounded-lg p-4 flex-1 overflow-y-auto font-mono text-sm min-h-0"
                  >
                    {selectedTask.progressMessages && selectedTask.progressMessages.length > 0 ? (
                      <div className="space-y-1">
                        {selectedTask.progressMessages.map((msg, index) => (
                          <div key={index} className="text-green-400 flex-shrink-0">
                            <span className="text-white/40 mr-2 text-xs">
                              {new Date(msg.timestamp).toLocaleTimeString()}
                            </span>
                            <span className="break-words">{msg.message}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-white/40">
                        {selectedTask.status === 'running' ? 'Waiting for log output...' : 'No log output available'}
                      </div>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center text-white/60">
                  <p className="text-lg mb-2">Select a task to view details</p>
                  <p className="text-sm">Choose from Running, Review, or Failed tasks</p>
                </div>
              </div>
            )}
          </div>
        </Panel>

        {/* Right Sidebar - Diff Preview & PR Management */}
        {selectedTask && (
          <>
            <PanelResizeHandle className="w-1 bg-white/10 hover:bg-purple-500/50 cursor-col-resize transition-colors relative group">
              <div className="absolute inset-y-0 -left-1 -right-1 group-hover:bg-purple-500/20" />
            </PanelResizeHandle>

            <Panel defaultSize={25} minSize={20} maxSize={40}>
              <div className="h-full bg-gray-800/50 border-l border-white/10 flex flex-col">
                {/* Diff Preview */}
                <div className="flex-1 p-6">
                  <div className="mb-4">
                    <h3 className="text-lg font-medium text-yellow-400 mb-2">Diff preview</h3>
                    {selectedTask.pr_url && (
                      <p className="text-sm text-white/60 mb-2">ui/theme/tokens.css</p>
                    )}
                  </div>
                  
                  <div className="bg-black/50 rounded-lg p-4 h-64 overflow-y-auto font-mono text-xs">
                    {prDiff ? (
                      <div className="space-y-1">
                        {prDiff.split('\n').map((line, index) => (
                          <div key={index} className={clsx(
                            line.startsWith('---') && 'text-red-400',
                            line.startsWith('+++') && 'text-green-400',
                            line.startsWith('@@') && 'text-blue-400',
                            line.startsWith('-') && !line.startsWith('---') && 'text-red-300 bg-red-500/10',
                            line.startsWith('+') && !line.startsWith('+++') && 'text-green-300 bg-green-500/10',
                            !line.startsWith('-') && !line.startsWith('+') && !line.startsWith('@') && 'text-white/60'
                          )}>
                            {line || ' '}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-white/40">
                        {selectedTask.status === 'running' ? 'Generating changes...' : 'No diff available'}
                      </div>
                    )}
                  </div>
                </div>

                {/* Pull Request Section */}
                {selectedTask.pr_url && (
                  <div className="p-6 border-t border-white/10">
                    <div className="mb-4">
                      <h3 className="text-lg font-medium text-yellow-400 mb-2">Pull request</h3>
                      <a 
                        href={selectedTask.pr_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-sm text-blue-400 hover:text-blue-300 underline"
                      >
                        {selectedTask.pr_url.replace('https://github.com/', '')}
                      </a>
                    </div>
                    
                    <div className="flex space-x-2">
                      {selectedTask.status === 'review' && (
                        <>
                          <button
                            onClick={() => handleApproveTask(selectedTask.id)}
                            className="flex-1 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => handleRetryTask(selectedTask.id)}
                            className="flex-1 bg-orange-600 hover:bg-orange-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
                          >
                            Retry
                          </button>
                        </>
                      )}
                      
                      {selectedTask.status === 'failed' && (
                        <button
                          onClick={() => handleRetryTask(selectedTask.id)}
                          className="w-full bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
                        >
                          Retry
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </Panel>
          </>
        )}
      </PanelGroup>
    </div>
  )
}

// Task Category Component
interface TaskCategoryProps {
  title: string
  tasks: Task[]
  selectedTask: Task | null
  onTaskSelect: (task: Task) => void
  getElapsedTime: (task: Task) => string
  getTaskChain: (task: Task) => string[]
}

const TaskCategory: React.FC<TaskCategoryProps> = ({
  title,
  tasks,
  selectedTask,
  onTaskSelect,
  getElapsedTime,
  getTaskChain
}) => {
  return (
    <div className="p-4 border-b border-white/5">
      <h3 className="text-sm font-medium text-yellow-400 mb-3">{title}</h3>
      
      <div className="space-y-2">
        {tasks.map((task) => (
          <motion.div
            key={task.id}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => onTaskSelect(task)}
            className={clsx(
              'p-3 rounded-lg cursor-pointer transition-all',
              'bg-white/5 hover:bg-white/10',
              selectedTask?.id === task.id && 'bg-purple-500/20 border border-purple-500/50'
            )}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1 min-w-0">
                <h4 className="text-sm font-medium text-white truncate">
                  {task.task_number} • {task.title}
                </h4>
                <p className="text-xs text-white/60 mt-1">
                  {task.agent || 'feature-builder'} • {task.status === 'running' ? 'Running' : task.status}
                </p>
              </div>
              
              {task.status === 'running' && (
                <div className="flex items-center ml-2">
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
                </div>
              )}
              
              {task.status === 'failed' && (
                <div className="flex items-center ml-2">
                  <div className="w-2 h-2 bg-red-400 rounded-full"></div>
                </div>
              )}
            </div>
            
            <div className="text-xs text-white/50">
              {task.started_at && `${getElapsedTime(task)} • `}
              {getTaskChain(task).join(' → ')}
            </div>
          </motion.div>
        ))}
        
        {tasks.length === 0 && (
          <div className="text-center py-4 text-white/40 text-sm">
            No {title.toLowerCase()} tasks
          </div>
        )}
      </div>
    </div>
  )
}