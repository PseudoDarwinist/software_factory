/**
 * PlanStage - Kanban board for task management and agent execution
 * 
 * This component implements the Plan stage of the Mission Control workflow:
 * - Kanban view with Ready, In Progress, Done columns
 * - Task cards showing title, owner, effort, and requirements
 * - Start button to launch agents (claude-code, goose, jacob)
 * - Side panel for task context and agent selection
 * - Real-time progress updates via WebSocket
 * - Retry functionality for failed tasks
 * - Dependency blocking visualization
 * 
 * Requirements addressed:
 * - Requirement 4: Task execution and agent orchestration
 * - Requirement 10: Real-time progress tracking
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { io, Socket } from 'socket.io-client';
import { LiquidCard } from '@/components/core/LiquidCard'
import missionControlApi from '@/services/api/missionControlApi'
import type { Task, TaskContext, Agent } from '@/types'
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";

interface PlanStageProps {
  selectedProject: string | null
  onStageChange?: (stage: string) => void
}

const AGENTS: Agent[] = [
  { id: 'feature-builder', name: 'Agent - Feature Builder', description: 'full repo write • best for feature work' },
  { id: 'test-runner', name: 'Agent - Test Runner', description: 'runs tests • fixes failing tests' },
  { id: 'code-reviewer', name: 'Agent - Code Reviewer', description: 'read-only quality & security review' },
  { id: 'debugger', name: 'Agent - Debugger', description: 'reproduce failure • minimal fix' },
  { id: 'design-to-code', name: 'Agent - Design to Code', description: 'converts designs to implementation' }
]

export const PlanStage: React.FC<PlanStageProps> = ({
  selectedProject,
  onStageChange
}) => {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [showSidePanel, setShowSidePanel] = useState(false)
  const [taskContext, setTaskContext] = useState<TaskContext | null>(null)
  const [selectedAgent, setSelectedAgent] = useState<string>('')
  const [isStarting, setIsStarting] = useState(false)
  const [socket, setSocket] = useState<Socket | null>(null);
  const [sidePanelWidth, setSidePanelWidth] = useState(384) // 24rem = 384px

  // Fetch initial tasks from API
  const fetchTasks = useCallback(async () => {
    if (!selectedProject) return

    try {
      setLoading(true)
      setError(null)
      
      const tasksData = await missionControlApi.getTasks(selectedProject)
      setTasks(tasksData)
    } catch (err) {
      console.error('Error fetching tasks:', err)
      setError(err instanceof Error ? err.message : 'Failed to fetch tasks')
    } finally {
      setLoading(false)
    }
  }, [selectedProject])

  // Load initial tasks on mount and project change
  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])
  
  // WebSocket connection for real-time updates
  useEffect(() => {
    // Connect to the WebSocket server
    const newSocket = io('http://localhost:8000'); // Adjust URL if needed
    setSocket(newSocket);

    newSocket.on('connect', () => {
      console.log('WebSocket connected:', newSocket.id);
      // You might need to send an authentication token here
      // newSocket.emit('authenticate', { token: 'your_jwt_token' });
    });

    newSocket.on('task_progress', (updatedTask: Task) => {
      console.log('Received task update:', updatedTask);
      setTasks(prevTasks => {
        const taskIndex = prevTasks.findIndex(t => t.id === updatedTask.id);
        if (taskIndex !== -1) {
          // Task exists, update it
          const newTasks = [...prevTasks];
          newTasks[taskIndex] = updatedTask;
          return newTasks;
        } else {
          // New task, add it to the list
          return [...prevTasks, updatedTask];
        }
      });
    });

    newSocket.on('disconnect', () => {
      console.log('WebSocket disconnected');
    });

    return () => {
      newSocket.disconnect();
    };
  }, []);

  // Subscribe to updates for active tasks
  useEffect(() => {
    if (socket && tasks.length > 0) {
      tasks.forEach(task => {
        // Subscribe to tasks that are not in a final state
        if (task.status !== 'done' && task.status !== 'failed') {
          console.log(`Subscribing to task ${task.id}`);
          socket.emit('subscribe_task', { taskId: task.id });
        }
      });
    }

    // The cleanup function will run when the component unmounts or deps change.
    return () => {
      if (socket && tasks.length > 0) {
        tasks.forEach(task => {
          if (task.status !== 'done' && task.status !== 'failed') {
            console.log(`Unsubscribing from task ${task.id}`);
            socket.emit('unsubscribe_task', { taskId: task.id });
          }
        });
      }
    };
  }, [socket, tasks]);


  // Group tasks by status
  const tasksByStatus = useMemo(() => {
    const grouped = {
      ready: [] as Task[],
      running: [] as Task[],
      review: [] as Task[],
      done: [] as Task[],
      failed: [] as Task[]
    }

    tasks.forEach(task => {
      if (grouped[task.status]) {
        grouped[task.status].push(task)
      }
    })

    return grouped
  }, [tasks])

  // Handle task selection and context loading
  const handleTaskSelect = useCallback(async (task: Task) => {
    setSelectedTask(task)
    setShowSidePanel(true)
    
    // Load task context
    try {
      const contextData = await missionControlApi.getTaskContext(task.id)
      setTaskContext(contextData)
    } catch (err) {
      console.error('Error loading task context:', err)
    }

    // Pre-select previous agent if retrying
    if (task.status === 'failed' && task.agent) {
      setSelectedAgent(task.agent)
    } else {
      setSelectedAgent('')
    }
  }, [])

  // Handle task start/retry
  const handleStartTask = useCallback(async (contextOptions: any, branchName: string, baseBranch: string) => {
    if (!selectedTask || !selectedAgent) return

    // Immediately close the panel for a better user experience
    setShowSidePanel(false)
    setSelectedTask(null)
    setTaskContext(null)
    setSelectedAgent('')
    setIsStarting(true)

    try {
      if (selectedTask.status === 'failed') {
        await missionControlApi.retryTask(selectedTask.id, selectedAgent)
      } else {
        await missionControlApi.startTask(selectedTask.id, selectedAgent, {
          contextOptions,
          branchName,
          baseBranch
        })
      }
      // No longer need to manually call fetchTasks() here.
      // The WebSocket 'task_progress' event will handle UI updates.
    } catch (err) {
      console.error('Error starting task:', err)
      // If the start fails, we should probably show an error and maybe reopen the panel
      // For now, an alert will suffice.
      alert(err instanceof Error ? `Failed to start task: ${err.message}` : 'Failed to start task')
      // Optionally, refetch tasks on failure to reset state
      fetchTasks()
    } finally {
      setIsStarting(false)
    }
    // Switch to Build stage so the user can monitor live logs
    if (onStageChange) {
      onStageChange('build')
    }
  }, [selectedTask, selectedAgent, fetchTasks])

  // Handle task cancellation
  const handleCancelTask = useCallback(async (taskId: string) => {
    try {
      const confirmed = window.confirm('Are you sure you want to cancel this task? This will stop the agent execution.')
      if (!confirmed) return

      await missionControlApi.cancelTask(taskId)
      
      // Refresh tasks to show updated status
      await fetchTasks()
      
    } catch (err) {
      console.error('Error cancelling task:', err)
      alert(err instanceof Error ? err.message : 'Failed to cancel task')
    }
  }, [fetchTasks])

  // Check if task is blocked by dependencies
  const isTaskBlocked = useCallback((task: Task) => {
    if (!task.depends_on || task.depends_on.length === 0) return false
    
    return task.depends_on.some(depId => {
      const depTask = tasks.find(t => t.id === depId)
      return depTask && depTask.status !== 'done'
    })
  }, [tasks])

  // Get blocking task names
  const getBlockingTasks = useCallback((task: Task) => {
    if (!task.depends_on) return []
    
    return task.depends_on
      .map(depId => tasks.find(t => t.id === depId))
      .filter(Boolean)
      .filter(t => t!.status !== 'done')
      .map(t => t!.title)
  }, [tasks])

  // Handle field updates
  const handleUpdateField = useCallback(async (taskId: string, field: string, value: any) => {
    try {
      const response = await missionControlApi.updateTaskField(taskId, field, value)
      if (response.task) {
        // Update local state
        setTasks(prevTasks => 
          prevTasks.map(task => 
            task.id === taskId ? { ...task, ...response.task } : task
          )
        )
      }
    } catch (error) {
      console.error('Error updating task field:', error)
    }
  }, [])

  // Handle assignee suggestion
  const handleSuggestAssignee = useCallback(async (taskId: string) => {
    try {
      const suggestion = await missionControlApi.suggestAssignee(taskId)
      // Update local state with suggestion
      setTasks(prevTasks => 
        prevTasks.map(task => 
          task.id === taskId ? { 
            ...task, 
            suggested_owner: suggestion.assignee,
            assignment_confidence: suggestion.confidence,
            assignment_reasoning: suggestion.reasoning
          } : task
        )
      )
    } catch (error) {
      console.error('Error getting assignee suggestion:', error)
    }
  }, [])

  // Handle effort estimate suggestion
  const handleSuggestEstimate = useCallback(async (taskId: string) => {
    try {
      const suggestion = await missionControlApi.suggestEstimate(taskId)
      // Update local state with suggestion
      setTasks(prevTasks => 
        prevTasks.map(task => 
          task.id === taskId ? { 
            ...task, 
            effort_estimate_hours: suggestion.hours,
            effort_reasoning: suggestion.reasoning
          } : task
        )
      )
    } catch (error) {
      console.error('Error getting effort suggestion:', error)
    }
  }, [])

  // Handle agent suggestion
  const handleSuggestAgent = useCallback(async (taskId: string) => {
    try {
      const suggestion = await missionControlApi.suggestAgent(taskId)
      // Update local state with suggestion
      setTasks(prevTasks => 
        prevTasks.map(task => 
          task.id === taskId ? { 
            ...task, 
            suggested_agent: suggestion.agent,
            agent_reasoning: suggestion.reasoning
          } : task
        )
      )
    } catch (error) {
      console.error('Error getting agent suggestion:', error)
    }
  }, [])

  // Handle side panel resize
  const handleSidePanelResize = useCallback((e: React.MouseEvent) => {
    const startX = e.clientX
    const startWidth = sidePanelWidth

    const handleMouseMove = (e: MouseEvent) => {
      const deltaX = startX - e.clientX
      const newWidth = Math.max(320, Math.min(800, startWidth + deltaX)) // Min 320px, Max 800px
      setSidePanelWidth(newWidth)
    }

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)
  }, [sidePanelWidth])

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-white/20 border-t-white/80 rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-white/60">Loading tasks...</p>
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
    <div className="h-full flex flex-col p-6 space-y-4">
      {/* Header */}
      <div className="flex-shrink-0">
        <h1 className="text-2xl font-bold text-white mb-2">Plan</h1>
        <p className="text-white/60">Task execution launchpad</p>
      </div>

      {/* Kanban Columns */}
      <div className="flex-1 flex min-h-0">
        <PanelGroup direction="horizontal">
          <Panel defaultSize={33}>
            <KanbanColumn
              title="Ready"
              tasks={tasksByStatus.ready}
              onTaskSelect={handleTaskSelect}
              isTaskBlocked={isTaskBlocked}
              getBlockingTasks={getBlockingTasks}
              onUpdateField={handleUpdateField}
              onSuggestAssignee={handleSuggestAssignee}
              onSuggestEstimate={handleSuggestEstimate}
              onSuggestAgent={handleSuggestAgent}
              onCancelTask={handleCancelTask}
            />
          </Panel>
          <PanelResizeHandle className="w-1 bg-white/10 hover:bg-purple-500/50 cursor-col-resize transition-colors relative group">
            <div className="absolute inset-y-0 -left-1 -right-1 group-hover:bg-purple-500/20" />
          </PanelResizeHandle>
          <Panel defaultSize={33}>
            <KanbanColumn
              title="In Progress"
              tasks={[...tasksByStatus.running, ...tasksByStatus.review]}
              onTaskSelect={handleTaskSelect}
              isTaskBlocked={isTaskBlocked}
              getBlockingTasks={getBlockingTasks}
              onUpdateField={handleUpdateField}
              onSuggestAssignee={handleSuggestAssignee}
              onSuggestEstimate={handleSuggestEstimate}
              onSuggestAgent={handleSuggestAgent}
              onCancelTask={handleCancelTask}
            />
          </Panel>
          <PanelResizeHandle className="w-1 bg-white/10 hover:bg-purple-500/50 cursor-col-resize transition-colors relative group">
            <div className="absolute inset-y-0 -left-1 -right-1 group-hover:bg-purple-500/20" />
          </PanelResizeHandle>
          <Panel defaultSize={34}>
            <KanbanColumn
              title="Done"
              tasks={[...tasksByStatus.done, ...tasksByStatus.failed]}
              onTaskSelect={handleTaskSelect}
              isTaskBlocked={isTaskBlocked}
              getBlockingTasks={getBlockingTasks}
              onUpdateField={handleUpdateField}
              onSuggestAssignee={handleSuggestAssignee}
              onSuggestEstimate={handleSuggestEstimate}
              onSuggestAgent={handleSuggestAgent}
              onCancelTask={handleCancelTask}
            />
          </Panel>
        </PanelGroup>
      </div>

      {/* Side Panel with Resizable Handle */}
      <AnimatePresence>
        {showSidePanel && selectedTask && (
          <motion.div
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="fixed top-0 right-0 h-full z-50 flex"
          >
            {/* Resize Handle */}
            <div 
              className="w-1 bg-white/10 hover:bg-purple-500/50 cursor-col-resize transition-colors relative group"
              onMouseDown={handleSidePanelResize}
            >
              <div className="absolute inset-y-0 -left-1 -right-1 group-hover:bg-purple-500/20" />
            </div>
            <div style={{ width: sidePanelWidth }}>
              <PrepareAgentRunPanel
              task={selectedTask}
              taskContext={taskContext}
              selectedAgent={selectedAgent}
              onAgentSelect={setSelectedAgent}
              onStart={handleStartTask}
              onClose={() => {
                setShowSidePanel(false)
                setSelectedTask(null)
                setTaskContext(null)
                setSelectedAgent('')
              }}
              isStarting={isStarting}
              agents={AGENTS}
              projectId={selectedProject}
            />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

// Kanban Column Component
interface KanbanColumnProps {
  title: string
  tasks: Task[]
  onTaskSelect: (task: Task) => void
  isTaskBlocked: (task: Task) => boolean
  getBlockingTasks: (task: Task) => string[]
  onUpdateField: (taskId: string, field: string, value: any) => void
  onSuggestAssignee: (taskId: string) => void
  onSuggestEstimate: (taskId: string) => void
  onSuggestAgent: (taskId: string) => void
  onCancelTask: (taskId: string) => void
}

const KanbanColumn: React.FC<KanbanColumnProps> = ({
  title,
  tasks,
  onTaskSelect,
  isTaskBlocked,
  getBlockingTasks,
  onUpdateField,
  onSuggestAssignee,
  onSuggestEstimate,
  onSuggestAgent,
  onCancelTask
}) => {
  return (
    <div className="flex flex-col h-full bg-white/5 p-4 rounded-lg mx-2">
      <div className="flex-shrink-0 mb-4">
        <h2 className="text-xl font-semibold text-white mb-1">{title}</h2>
        <div className="text-sm text-white/60">{tasks.length} tasks</div>
      </div>
      
      <div className="flex-1 space-y-4 overflow-y-auto pr-2 min-h-0">
        {tasks.map((task, index) => (
          <TaskCard
            key={task.id}
            task={task}
            onSelect={() => onTaskSelect(task)}
            isBlocked={isTaskBlocked(task)}
            blockingTasks={getBlockingTasks(task)}
            index={index}
            onUpdateField={onUpdateField}
            onSuggestAssignee={onSuggestAssignee}
            onSuggestEstimate={onSuggestEstimate}
            onSuggestAgent={onSuggestAgent}
            onCancelTask={onCancelTask}
          />
        ))}
        
        {tasks.length === 0 && (
          <div className="text-center py-8 text-white/40">
            No tasks in {title.toLowerCase()}
          </div>
        )}
      </div>
    </div>
  )
}

// Task Card Component
interface TaskCardProps {
  task: Task
  onSelect: () => void
  isBlocked: boolean
  blockingTasks: string[]
  index: number
  onUpdateField: (taskId: string, field: string, value: any) => void
  onSuggestAssignee: (taskId: string) => void
  onSuggestEstimate: (taskId: string) => void
  onSuggestAgent: (taskId: string) => void
  onCancelTask: (taskId: string) => void
}

const TaskCard: React.FC<TaskCardProps> = ({
  task,
  onSelect,
  isBlocked,
  blockingTasks,
  index,
  onUpdateField,
  onSuggestAssignee,
  onSuggestEstimate,
  onSuggestAgent,
  onCancelTask
}) => {
  const getStatusColor = () => {
    switch (task.status) {
      case 'ready': return 'border-green-500/50'
      case 'running': return 'border-blue-500/50'
      case 'review': return 'border-yellow-500/50'
      case 'done': return 'border-gray-500/50'
      case 'failed': return 'border-red-500/50'
      default: return 'border-white/20'
    }
  }

  const getPriorityColor = () => {
    switch (task.priority) {
      case 'critical': return 'text-red-400'
      case 'high': return 'text-orange-400'
      case 'medium': return 'text-yellow-400'
      case 'low': return 'text-green-400'
      default: return 'text-white/60'
    }
  }

  const getProgressPercent = () => {
    const messages = task.progressMessages || (task as any).progressMessages
    if (!messages || messages.length === 0) return null
    const lastMessage = messages[messages.length - 1]
    return lastMessage.percent
  }

  const getLatestMessage = () => {
    const messages = task.progressMessages || (task as any).progressMessages
    if (!messages || messages.length === 0) return null
    const lastMessage = messages[messages.length - 1]
    return lastMessage.message
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="relative"
    >
      <LiquidCard
        variant="default"
        onClick={onSelect}
        className={clsx(
          'transition-all cursor-pointer hover:scale-105',
          getStatusColor(),
          isBlocked && 'opacity-50',
          task.status === 'failed' && 'relative'
        )}
      >
        {/* Failed task red corner badge */}
        {task.status === 'failed' && (
          <div className="absolute -top-2 -right-2 w-4 h-4 bg-red-500 rounded-full border-2 border-black"></div>
        )}

        <div className="p-4">
          {/* Task number and title */}
          <div className="mb-3">
            <div className="text-sm text-white/60 mb-1">{task.task_number}</div>
            <h3 className="font-semibold text-white leading-tight">
              {task.title}
            </h3>
          </div>

          {/* Avatar and progress */}
          <div className="flex items-center mb-3">
            <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center mr-3">
              <span className="text-xs text-white font-medium">
                {task.suggested_owner ? task.suggested_owner.charAt(0).toUpperCase() : '?'}
              </span>
            </div>
            
            {task.status === 'running' && getProgressPercent() && (
              <div className="flex items-center text-sm">
                <span className="text-yellow-400 mr-1">⚡</span>
                <span className="text-white font-medium">{getProgressPercent()}%</span>
              </div>
            )}
          </div>

          {/* Goal line from acceptance criteria */}
          {task.goal_line && (
            <div className="mb-3 p-2 bg-white/5 rounded text-xs text-white/80 italic">
              "{task.goal_line}"
            </div>
          )}

          {/* Task details with editable fields */}
          <div className="space-y-2 text-sm">
            {/* Assignee with Suggest button */}
            <div className="flex items-center justify-between">
              <span className="text-white/60">Assignee:</span>
              <div className="flex items-center space-x-2">
                <input
                  type="text"
                  value={task.assigned_to || task.suggested_owner || ''}
                  onChange={(e) => onUpdateField(task.id, 'assigned_to', e.target.value)}
                  className="bg-white/10 text-white text-xs px-2 py-1 rounded w-20 border-none outline-none"
                  placeholder="Unassigned"
                />
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onSuggestAssignee(task.id)
                  }}
                  className="text-xs bg-blue-500/20 text-blue-300 px-2 py-1 rounded hover:bg-blue-500/30 transition-colors"
                >
                  Suggest
                </button>
              </div>
            </div>
            
            {/* Show assignee reasoning if available */}
            {task.assignment_reasoning && (
              <div className="text-xs text-blue-300 italic">
                because {task.assignment_reasoning}
              </div>
            )}
            
            {/* Effort estimate with Suggest button */}
            <div className="flex items-center justify-between">
              <span className="text-white/60">Effort:</span>
              <div className="flex items-center space-x-2">
                <input
                  type="number"
                  value={task.effort_estimate_hours || ''}
                  onChange={(e) => onUpdateField(task.id, 'effort_estimate_hours', parseFloat(e.target.value) || 0)}
                  className="bg-white/10 text-white text-xs px-2 py-1 rounded w-16 border-none outline-none"
                  placeholder="0"
                  step="0.5"
                />
                <span className="text-white/60 text-xs">hrs</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    onSuggestEstimate(task.id)
                  }}
                  className="text-xs bg-green-500/20 text-green-300 px-2 py-1 rounded hover:bg-green-500/30 transition-colors"
                >
                  Suggest
                </button>
              </div>
            </div>
            
            {/* Show effort reasoning if available */}
            {task.effort_reasoning && (
              <div className="text-xs text-green-300 italic">
                because {task.effort_reasoning}
              </div>
            )}
            
            {/* Priority with color coding */}
            <div className="flex items-center justify-between">
              <span className="text-white/60">Priority:</span>
              <select
                value={task.priority}
                onChange={(e) => onUpdateField(task.id, 'priority', e.target.value)}
                className="bg-white/10 text-white text-xs px-2 py-1 rounded border-none outline-none"
                onClick={(e) => e.stopPropagation()}
              >
                <option value="low" className="bg-gray-800">Low</option>
                <option value="medium" className="bg-gray-800">Medium</option>
                <option value="high" className="bg-gray-800">High</option>
                <option value="critical" className="bg-gray-800">Critical</option>
              </select>
            </div>
            
            {/* Suggested agent */}
            {task.suggested_agent && (
              <div className="flex items-center justify-between">
                <span className="text-white/60">Agent:</span>
                <div className="flex items-center space-x-2">
                  <span className="text-white text-xs">{task.suggested_agent}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onSuggestAgent(task.id)
                    }}
                    className="text-xs bg-purple-500/20 text-purple-300 px-2 py-1 rounded hover:bg-purple-500/30 transition-colors"
                  >
                    Re-suggest
                  </button>
                </div>
              </div>
            )}
            
            {/* Show agent reasoning if available */}
            {task.agent_reasoning && (
              <div className="text-xs text-purple-300 italic">
                because {task.agent_reasoning}
              </div>
            )}
            
            {/* Likely touches hint */}
            {task.likely_touches && task.likely_touches.length > 0 && (
              <div className="flex items-center justify-between">
                <span className="text-white/60">Likely touches:</span>
                <span className="text-white/80 text-xs">{task.likely_touches.slice(0, 2).join(', ')}</span>
              </div>
            )}
            
            {task.requirements_refs && task.requirements_refs.length > 0 && (
              <div className="flex items-center justify-between">
                <span className="text-white/60">Requirements:</span>
                <span className="text-white">{task.requirements_refs.join(', ')}</span>
              </div>
            )}
          </div>

          {/* Progress message */}
          {task.status === 'running' && getLatestMessage() && (
            <div className="mt-3 p-2 bg-blue-500/20 rounded text-xs">
              <div className="text-blue-300 font-medium mb-1">
                {getProgressPercent() ? `${getProgressPercent()}% Complete` : 'In Progress'}
              </div>
              <div className="text-white/80">
                {getLatestMessage()}
              </div>
              {getProgressPercent() && (
                <div className="mt-2 bg-white/20 rounded-full h-1">
                  <div 
                    className="bg-blue-400 h-1 rounded-full transition-all duration-300"
                    style={{ width: `${getProgressPercent()}%` }}
                  />
                </div>
              )}
            </div>
          )}

          {/* Blocking message */}
          {isBlocked && (
            <div className="mt-3 p-2 bg-red-500/20 rounded text-xs text-red-300">
              Blocked by: {blockingTasks.join(', ')}
            </div>
          )}

          {/* Start button for ready tasks */}
          {task.status === 'ready' && !isBlocked && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onSelect()
              }}
              className="neon-btn neon-btn--gray w-full mt-4 py-2"
            >
              ⚡ Start Task
            </button>
          )}

          {/* Cancel button for running tasks */}
          {task.status === 'running' && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={(e) => {
                e.stopPropagation()
                onCancelTask(task.id)
              }}
              className="w-full mt-4 py-2 bg-orange-500/80 text-white font-semibold rounded-lg hover:bg-orange-500 transition-all"
            >
              ⏹️ Cancel Task
            </motion.button>
          )}

          {/* Retry button for failed tasks */}
          {task.status === 'failed' && (
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={(e) => {
                e.stopPropagation()
                onSelect()
              }}
              className="w-full mt-4 py-2 bg-red-500/80 text-white font-semibold rounded-lg hover:bg-red-500 transition-all"
            >
              🔄 Retry
            </motion.button>
          )}
        </div>
      </LiquidCard>
    </motion.div>
  )
}

// Prepare Agent Run Side Panel Component
interface PrepareAgentRunPanelProps {
  task: Task
  taskContext: TaskContext | null
  selectedAgent: string
  onAgentSelect: (agentId: string) => void
  onStart: (contextOptions: any, branchName: string, baseBranch: string) => void
  onClose: () => void
  isStarting: boolean
  agents: Agent[]
  projectId: string | null
}

const PrepareAgentRunPanel: React.FC<PrepareAgentRunPanelProps> = ({
  task,
  taskContext,
  selectedAgent,
  onAgentSelect,
  onStart,
  onClose,
  isStarting,
  agents,
  projectId
}) => {
  const [contextOptions, setContextOptions] = useState({
    spec_files: true,
    requirements: true,
    design: true,
    task: true,
    code_paths: true
  })

  const [branchName, setBranchName] = useState(() => {
    const taskTitle = task.title.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 30)
    const date = new Date().toISOString().slice(0, 10).replace(/-/g, '')
    return `feature/${task.id}-${taskTitle}-${date}`
  })

  const [baseBranch] = useState('main')
  const [githubStatus, setGithubStatus] = useState<{
    connected: boolean
    repo_accessible: boolean
    repo_url?: string
    base_branch?: string
    error?: string
  } | null>(null)

  // Load GitHub status on mount
  useEffect(() => {
    const loadGithubStatus = async () => {
      try {
        console.log('🔍 Loading GitHub status for project:', projectId)
        const status = await missionControlApi.getGitHubStatus(projectId || undefined)
        console.log('✅ GitHub status received:', status)
        setGithubStatus(status)
      } catch (error) {
        console.error('❌ Failed to load GitHub status:', error)
        setGithubStatus({ connected: false, repo_accessible: false, error: 'Failed to check status' })
      }
    }
    loadGithubStatus()
  }, [projectId])

  // Set default agent selection
  useEffect(() => {
    if (!selectedAgent && task.suggested_agent) {
      onAgentSelect(task.suggested_agent)
    } else if (!selectedAgent) {
      onAgentSelect('feature-builder') // Default to feature-builder
    }
  }, [selectedAgent, task.suggested_agent, onAgentSelect])

  const handleStart = () => {
    onStart(contextOptions, branchName, baseBranch)
  }

  const getDryRunSummary = () => {
    const agent = selectedAgent || 'feature-builder'
    const contextParts = []
    if (contextOptions.spec_files) contextParts.push('spec')
    if (contextOptions.requirements) contextParts.push('requirements')
    if (contextOptions.design) contextParts.push('design')
    if (contextOptions.task) contextParts.push('task')
    
    const contextStr = contextParts.length > 0 ? contextParts.join('+') : 'minimal context'
    const pathsStr = task.likely_touches?.join(', ') || 'suggested paths'
    
    return `Create branch from ${baseBranch}, pass ${contextStr}, limit writes to ${pathsStr}, run tests, push, open draft PR.`
  }

  const canStart = githubStatus?.connected && githubStatus?.repo_accessible && selectedAgent && !isStarting

  return (
    <div className="h-full w-full bg-gray-900/95 backdrop-blur-lg border-l border-gray-700/50 flex flex-col shadow-2xl">
      {/* Header */}
      <div className="p-6 border-b border-gray-700/50 bg-gray-800/50">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xl font-bold text-white">Plan • Prepare Agent Run</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-gray-700/50 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        <p className="text-sm text-gray-300">
          Task: {task.task_number} — {task.title}
        </p>
      </div>
      {/* Content - Scrollable */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800">
        {/* Preflight Status */}
        <div className={clsx(
          'rounded-xl p-4 border backdrop-blur-sm',
          githubStatus?.connected && githubStatus?.repo_accessible
            ? 'bg-green-500/10 border-green-500/30 shadow-lg shadow-green-500/5'
            : 'bg-red-500/10 border-red-500/30 shadow-lg shadow-red-500/5'
        )}>
          {githubStatus?.connected && githubStatus?.repo_accessible ? (
            <div>
              <div className="flex items-center space-x-2 mb-1">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                <span className="text-sm text-green-400 font-medium">GitHub connected</span>
              </div>
              <div className="text-xs text-gray-400">
                {githubStatus.repo_url} • base: {githubStatus.base_branch || 'main'}
              </div>
            </div>
          ) : (
            <div>
              <div className="flex items-center space-x-2 mb-2">
                <div className="w-2 h-2 bg-red-400 rounded-full animate-pulse"></div>
                <span className="text-sm text-red-400 font-medium">GitHub not connected</span>
              </div>
              <button className="text-xs text-blue-400 hover:text-blue-300 underline transition-colors">
                Connect GitHub
              </button>
            </div>
          )}
        </div>

        {/* Dry-run Summary */}
        <div className="bg-gray-800/50 rounded-xl p-4 border border-gray-700/30 shadow-lg">
          <div className="text-sm text-gray-300 mb-2 font-medium">What will happen:</div>
          <div className="text-xs text-gray-400 leading-relaxed bg-gray-900/30 rounded-lg p-3 border border-gray-700/20">
            {getDryRunSummary()}
          </div>
        </div>

        {/* 1. Agent Profile */}
        <div>
          <h3 className="text-lg font-semibold text-blue-400 mb-4 flex items-center">
            <span className="bg-blue-500/20 text-blue-400 rounded-full w-6 h-6 flex items-center justify-center text-sm mr-2">1</span>
            Agent profile
          </h3>
          <div className="space-y-3">
            {agents.map((agent) => (
              <label
                key={agent.id}
                className={clsx(
                  'flex items-start space-x-3 p-4 rounded-xl cursor-pointer transition-all border backdrop-blur-sm',
                  selectedAgent === agent.id
                    ? 'bg-blue-500/10 border-blue-500/30 shadow-lg shadow-blue-500/5'
                    : 'bg-gray-800/30 border-gray-700/30 hover:bg-gray-700/30 hover:border-gray-600/40'
                )}
              >
                <input
                  type="radio"
                  name="agent"
                  value={agent.id}
                  checked={selectedAgent === agent.id}
                  onChange={() => onAgentSelect(agent.id)}
                  className="mt-1 text-blue-400 focus:ring-blue-400 focus:ring-offset-gray-900"
                />
                <div>
                  <div className="text-sm font-medium text-white">{agent.name}</div>
                  <div className="text-xs text-gray-400">{agent.description}</div>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* 2. Context Groups */}
        <div>
          <h3 className="text-lg font-semibold text-purple-400 mb-4 flex items-center">
            <span className="bg-purple-500/20 text-purple-400 rounded-full w-6 h-6 flex items-center justify-center text-sm mr-2">2</span>
            Context groups
          </h3>
          <div className="space-y-3">
            {[
              { key: 'spec_files', label: 'Spec files', desc: 'requirements.md, design.md', checked: contextOptions.spec_files },
              { key: 'requirements', label: 'Requirements', desc: 'acceptance criteria and user stories', checked: contextOptions.requirements },
              { key: 'design', label: 'Design notes', desc: 'design documents and mockups', checked: contextOptions.design },
              { key: 'task', label: 'Task text', desc: `task description and goals`, checked: contextOptions.task },
              { key: 'code_paths', label: 'Suggested code paths', desc: task.likely_touches?.join(' • ') || 'likely files to modify', checked: contextOptions.code_paths }
            ].map((option) => (
              <label key={option.key} className="flex items-start space-x-3 cursor-pointer p-3 rounded-lg hover:bg-gray-800/30 transition-colors">
                <input
                  type="checkbox"
                  checked={option.checked}
                  onChange={(e) => setContextOptions(prev => ({ ...prev, [option.key]: e.target.checked }))}
                  className="mt-1 text-purple-400 focus:ring-purple-400 focus:ring-offset-gray-900 rounded"
                />
                <div>
                  <div className="text-sm font-medium text-white">{option.label}</div>
                  <div className="text-xs text-gray-400">{option.desc}</div>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* 3. Branch Name */}
        <div>
          <h3 className="text-lg font-semibold text-orange-400 mb-4 flex items-center">
            <span className="bg-orange-500/20 text-orange-400 rounded-full w-6 h-6 flex items-center justify-center text-sm mr-2">3</span>
            Branch name
          </h3>
          <div className="text-xs text-gray-400 mb-3 bg-gray-800/30 rounded-lg p-2 border border-gray-700/30">
            Base branch: <span className="text-orange-400 font-mono">{baseBranch}</span>
          </div>
          <input
            type="text"
            value={branchName}
            onChange={(e) => setBranchName(e.target.value)}
            className="w-full bg-gray-800/50 text-white text-sm px-4 py-3 rounded-xl border border-gray-700/30 focus:border-orange-400 focus:outline-none focus:ring-2 focus:ring-orange-400/20 transition-all font-mono"
            placeholder={`feature/${task.id}-task-name-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}`}
          />
        </div>
      </div>

      {/* Footer - Fixed at bottom */}
      <div className="p-6 border-t border-gray-700/50 bg-gray-800/30 backdrop-blur-sm">
        {canStart ? (
          <button
            onClick={handleStart}
            disabled={isStarting}
            className={clsx(
              'neon-btn w-full py-3',
              isStarting 
                ? 'neon-btn--disabled cursor-not-allowed' 
                : 'neon-btn--gray'
            )}
          >
            {isStarting ? (
              <div className="flex items-center justify-center space-x-2">
                <div className="w-4 h-4 border-2 border-gray-300/30 border-t-gray-300 rounded-full animate-spin"></div>
                <span>Starting...</span>
              </div>
            ) : (
              '⚡ Start Agent Run'
            )}
          </button>
        ) : (
          <button
            onClick={() => alert('Please set up GitHub integration first')}
            className="neon-btn neon-btn--blue w-full py-3"
          >
            Connect GitHub
          </button>
        )}
      </div>
    </div>
  )
}

export default PlanStage