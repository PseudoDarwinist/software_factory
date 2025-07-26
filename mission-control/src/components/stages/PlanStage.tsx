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
  { id: 'claude-code', name: 'Claude Code', description: 'Advanced code generation and refactoring' },
  { id: 'goose', name: 'Goose', description: 'Rapid prototyping and iteration' },
  { id: 'jacob', name: 'Jacob', description: 'Full-stack development and testing' }
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
  const handleStartTask = useCallback(async () => {
    if (!selectedTask || !selectedAgent) return

    try {
      setIsStarting(true)
      
      if (selectedTask.status === 'failed') {
        await missionControlApi.retryTask(selectedTask.id, selectedAgent)
      } else {
        await missionControlApi.startTask(selectedTask.id, selectedAgent)
      }

      // Close side panel and refresh tasks
      setShowSidePanel(false)
      setSelectedTask(null)
      setTaskContext(null)
      setSelectedAgent('')
      
      // Refresh tasks to show updated status
      await fetchTasks()
      
    } catch (err) {
      console.error('Error starting task:', err)
      alert(err instanceof Error ? err.message : 'Failed to start task')
    } finally {
      setIsStarting(false)
    }
  }, [selectedTask, selectedAgent, fetchTasks])

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
    <div className="h-full flex flex-col">
      {/* Main Kanban Board */}
      <div className="flex-1 flex flex-col p-6">
        {/* Header */}
        <div className="flex-shrink-0 mb-6">
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
              />
            </Panel>
          </PanelGroup>
        </div>
      </div>

      {/* Side Panel */}
      <AnimatePresence>
        {showSidePanel && selectedTask && (
          <motion.div
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="w-96 bg-black/20 backdrop-blur-md border-l border-white/10 flex flex-col"
          >
            <TaskSidePanel
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
            />
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
}

const KanbanColumn: React.FC<KanbanColumnProps> = ({
  title,
  tasks,
  onTaskSelect,
  isTaskBlocked,
  getBlockingTasks
}) => {
  return (
    <div className="flex flex-col h-full bg-white/5 p-4 rounded-lg mx-2">
      <div className="flex-shrink-0 mb-4">
        <h2 className="text-xl font-semibold text-white mb-1">{title}</h2>
        <div className="text-sm text-white/60">{tasks.length} tasks</div>
      </div>
      
      <div className="flex-1 space-y-4 overflow-y-auto min-h-0">
        {tasks.map((task, index) => (
          <TaskCard
            key={task.id}
            task={task}
            onSelect={() => onTaskSelect(task)}
            isBlocked={isTaskBlocked(task)}
            blockingTasks={getBlockingTasks(task)}
            index={index}
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
}

const TaskCard: React.FC<TaskCardProps> = ({
  task,
  onSelect,
  isBlocked,
  blockingTasks,
  index
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

          {/* Task details */}
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-white/60">Suggested:</span>
              <span className="text-white">{task.suggested_owner || 'Unassigned'}</span>
            </div>
            
            {task.effort_estimate_hours && (
              <div className="flex items-center justify-between">
                <span className="text-white/60">Effort:</span>
                <span className="text-white">{task.effort_estimate_hours} hours</span>
              </div>
            )}
            
            <div className="flex items-center justify-between">
              <span className="text-white/60">Priority:</span>
              <span className={getPriorityColor()}>
                {task.priority.charAt(0).toUpperCase() + task.priority.slice(1)}
              </span>
            </div>
            
            {task.requirements_refs && task.requirements_refs.length > 0 && (
              <div className="flex items-center justify-between">
                <span className="text-white/60">Requirements:</span>
                <span className="text-white">{task.requirements_refs.join(', ')}</span>
              </div>
            )}
          </div>

          {/* Progress message */}
          {task.status === 'running' && getLatestMessage() && (
            <div className="mt-3 p-2 bg-white/10 rounded text-xs text-white/80">
              {getLatestMessage()}
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
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={(e) => {
                e.stopPropagation()
                onSelect()
              }}
              className="w-full mt-4 py-2 bg-gradient-to-r from-green-400 to-blue-500 text-black font-semibold rounded-lg hover:from-green-500 hover:to-blue-600 transition-all"
            >
              ⚡ Start Task
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

// Task Side Panel Component
interface TaskSidePanelProps {
  task: Task
  taskContext: TaskContext | null
  selectedAgent: string
  onAgentSelect: (agentId: string) => void
  onStart: () => void
  onClose: () => void
  isStarting: boolean
  agents: Agent[]
}

const TaskSidePanel: React.FC<TaskSidePanelProps> = ({
  task,
  taskContext,
  selectedAgent,
  onAgentSelect,
  onStart,
  onClose,
  isStarting,
  agents
}) => {
  return (
    <>
      {/* Header */}
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-white">
            {task.status === 'failed' ? 'Retry Task' : 'Start Task'}
          </h3>
          <button
            onClick={onClose}
            className="text-white/60 hover:text-white/80 p-1"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <p className="text-sm text-white/70 mt-1">
          {task.task_number} - {task.title}
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* Task Context */}
        {taskContext && (
          <div>
            <h4 className="text-sm font-medium text-white/80 mb-3">Context Summary</h4>
            <div className="bg-white/5 rounded-lg p-3 max-h-40 overflow-y-auto">
              <pre className="text-xs text-white/70 whitespace-pre-wrap">
                {taskContext.context.substring(0, 500)}
                {taskContext.context.length > 500 && '...'}
              </pre>
            </div>
          </div>
        )}

        {/* Agent Selection */}
        <div>
          <h4 className="text-sm font-medium text-white/80 mb-3">Select Agent</h4>
          <div className="space-y-2">
            {agents.map((agent) => (
              <label
                key={agent.id}
                className={clsx(
                  'flex items-start space-x-3 p-3 rounded-lg cursor-pointer transition-all',
                  selectedAgent === agent.id
                    ? 'bg-blue-500/20 border border-blue-500/50'
                    : 'bg-white/5 hover:bg-white/10'
                )}
              >
                <input
                  type="radio"
                  name="agent"
                  value={agent.id}
                  checked={selectedAgent === agent.id}
                  onChange={() => onAgentSelect(agent.id)}
                  className="mt-1"
                />
                <div>
                  <div className="text-sm font-medium text-white">{agent.name}</div>
                  <div className="text-xs text-white/60">{agent.description}</div>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Previous execution info for retries */}
        {task.status === 'failed' && task.agent && (
          <div>
            <h4 className="text-sm font-medium text-white/80 mb-3">Previous Execution</h4>
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
              <div className="text-sm text-white mb-2">
                <strong>Agent:</strong> {task.agent}
              </div>
              {task.error && (
                <div className="text-xs text-red-300">
                  <strong>Error:</strong> {task.error}
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-white/10">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={onStart}
          disabled={!selectedAgent || isStarting}
          className={clsx(
            'w-full py-3 rounded-lg font-semibold transition-all',
            selectedAgent && !isStarting
              ? 'bg-gradient-to-r from-green-400 to-blue-500 text-black hover:from-green-500 hover:to-blue-600'
              : 'bg-white/10 text-white/50 cursor-not-allowed'
          )}
        >
          {isStarting ? (
            <div className="flex items-center justify-center space-x-2">
              <div className="w-4 h-4 border-2 border-white/20 border-t-white/80 rounded-full animate-spin"></div>
              <span>Starting...</span>
            </div>
          ) : (
            `🚀 ${task.status === 'failed' ? 'Retry' : 'Run'}`
          )}
        </motion.button>
      </div>
    </>
  )
}

export default PlanStage