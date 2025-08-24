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

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { clsx } from 'clsx'
import { io, Socket } from 'socket.io-client';
import { LiquidCard } from '@/components/core/LiquidCard'
import { GlassBackground } from '@/components/core/GlassBackground'
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

// Work Order Enhancement - Primary view for transforming tasks to work orders

export const PlanStage: React.FC<PlanStageProps> = ({
  selectedProject,
  onStageChange
}) => {
  // Work Order Enhancement state
  const [activeView, setActiveView] = useState<'work-order-enhancement' | 'task-execution'>('work-order-enhancement');
  const [workOrdersGenerated, setWorkOrdersGenerated] = useState(false);
  const [generationStatus, setGenerationStatus] = useState<'idle' | 'generating' | 'completed' | 'error'>('idle');
  const [workOrders, setWorkOrders] = useState<any[]>([]);
  const [selectedWorkOrder, setSelectedWorkOrder] = useState<any>(null);
  const [showWorkOrderModal, setShowWorkOrderModal] = useState(false);
  const initialLoad = useRef(true);
  
  // Existing task management state
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [showSidePanel, setShowSidePanel] = useState(false);
  const [taskContext, setTaskContext] = useState<TaskContext | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<string>('')
  const [isStarting, setIsStarting] = useState(false)
  const [socket, setSocket] = useState<Socket | null>(null);
  const [sidePanelWidth, setSidePanelWidth] = useState(384) // 24rem = 384px
  
  // View selection and work order management

  // Fetch initial tasks from API
  const fetchTasks = useCallback(async () => {
    if (!selectedProject) return

    try {
      setLoading(true)
      setError(null)
      
      const tasksData = await missionControlApi.getTasks(selectedProject)
      console.log('Fetched tasks data:', tasksData);
      setTasks(tasksData)

      // Only set the view on the initial load to avoid overriding user selection
      if (initialLoad.current) {
        const hasWorkOrders = await missionControlApi.getWorkOrders(`spec_${selectedProject}`, selectedProject).then(wos => wos.length > 0);
        if (hasWorkOrders) {
          setWorkOrdersGenerated(true);
          setActiveView('task-execution');
      } else {
          setWorkOrdersGenerated(false);
          setActiveView('work-order-enhancement');
        }
        initialLoad.current = false;
      }
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
  }, [selectedProject]);

  // Subscribe to updates for active tasks
  useEffect(() => {
    if (socket && tasks.length > 0) {
      tasks.forEach(task => {
        // Subscribe to tasks that are not in a final state
        if (task.status !== 'done' && task.status !== 'failed') {
          console.log(`Subscribing to task ${task.id}`);
          // Ensure a JSON object is sent for subscription
          socket.emit('subscribe_task', { type: 'task_progress', id: task.id });
        }
      });
    }

    // The cleanup function will run when the component unmounts or deps change.
    return () => {
      if (socket && tasks.length > 0) {
        tasks.forEach(task => {
          if (task.status !== 'done' && task.status !== 'failed') {
            console.log(`Unsubscribing from task ${task.id}`);
            // Ensure a JSON object is sent for unsubscription
            socket.emit('unsubscribe_task', { type: 'task_progress', id: task.id });
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

  // Get dependency status for a task
  const getDependencyStatus = useCallback((task: Task) => {
    if (!task.depends_on || task.depends_on.length === 0) {
      return { total: 0, completed: 0, blocked: false }
    }
    
    const dependencies = task.depends_on
      .map(depId => tasks.find(t => t.id === depId))
      .filter(Boolean)
    
    const completed = dependencies.filter(dep => dep!.status === 'done').length
    const total = dependencies.length
    const blocked = completed < total
    
    return { total, completed, blocked }
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

  // Handle work order selection and modal display
  const handleWorkOrderSelect = useCallback((workOrder: any) => {
    setSelectedWorkOrder(workOrder)
    setShowWorkOrderModal(true)
  }, [])

  const handleCloseWorkOrderModal = useCallback(() => {
    setShowWorkOrderModal(false)
    setSelectedWorkOrder(null)
  }, [])

  // Generate implementation plan for a work order
  const handleGenerateImplementation = useCallback(async (workOrderId: string) => {
    try {
      // TODO: Implement API call to generate implementation plan
      console.log('Generating implementation plan for work order:', workOrderId)
      // const implementationPlan = await missionControlApi.generateImplementationPlan(workOrderId)
      // Update work order with implementation plan
      // setWorkOrders(prev => prev.map(wo => wo.id === workOrderId ? { ...wo, implementation_plan: implementationPlan } : wo))
    } catch (error) {
      console.error('Error generating implementation plan:', error)
    }
  }, [])

  // Persist work orders to ensure they don't disappear when navigating stages
  useEffect(() => {
    if (workOrders.length > 0) {
      // Store work orders in localStorage as a fallback
      const storageKey = `work-orders-${selectedProject}`
      localStorage.setItem(storageKey, JSON.stringify(workOrders))
    }
  }, [workOrders, selectedProject])

  // Load persisted work orders on component mount
  useEffect(() => {
    if (selectedProject) {
      const storageKey = `work-orders-${selectedProject}`
      const storedWorkOrders = localStorage.getItem(storageKey)
      if (storedWorkOrders) {
        try {
          const parsed = JSON.parse(storedWorkOrders)
          if (parsed.length > 0) {
            setWorkOrders(parsed)
            setWorkOrdersGenerated(true)
            setGenerationStatus('completed')
          } else {
            // If stored work orders is empty, reset to idle state
            setWorkOrders([])
            setWorkOrdersGenerated(false)
            setGenerationStatus('idle')
          }
        } catch (error) {
          console.error('Error loading stored work orders:', error)
          // Reset to idle state on error
          setWorkOrders([])
          setWorkOrdersGenerated(false)
          setGenerationStatus('idle')
        }
      } else {
        // No stored work orders, reset to idle state
        setWorkOrders([])
        setWorkOrdersGenerated(false)
        setGenerationStatus('idle')
      }
    }
  }, [selectedProject])

  // Load work orders when component mounts or project changes
  const loadWorkOrders = useCallback(async () => {
    if (!selectedProject) return
    
    try {
      const specId = `spec_${selectedProject}`
      const workOrdersData = await missionControlApi.getWorkOrders(specId, selectedProject)
      setWorkOrders(workOrdersData)
      
      const status = await missionControlApi.getWorkOrderGenerationStatus(specId, selectedProject)
      if (status.status === 'completed') {
        setWorkOrdersGenerated(true)
        setGenerationStatus('completed')
      } else if (status.generated_work_orders > 0) {
        setWorkOrdersGenerated(true)
        setGenerationStatus('idle')
      }
    } catch (error) {
      console.error('Error loading work orders:', error)
    }
  }, [selectedProject])

  // Generate work orders with AI streaming
  const handleGenerateWorkOrders = useCallback(async () => {
    if (!selectedProject) return

    try {
      setGenerationStatus('generating')
      setWorkOrders([]) // Clear existing work orders
      const specId = `spec_${selectedProject}`
      
      const stream = await missionControlApi.generateWorkOrders(specId, selectedProject)
      const reader = stream.getReader()
      const decoder = new TextDecoder()

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.trim() && line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              console.log('Work order generation event:', data)

              if (data.type === 'work_order_created' && data.work_order) {
                // Add work order to list with proper validation
                setWorkOrders(prev => {
                  const currentOrders = Array.isArray(prev) ? prev : []
                  return [...currentOrders, data.work_order]
                })
              } else if (data.type === 'generation_completed') {
                console.log('Work order generation completed')
                setGenerationStatus('completed')
                setWorkOrdersGenerated(true)
                // Stay in work-order-enhancement view to show results
                // Don't auto-switch to task execution
              } else if (data.type === 'generation_skipped') {
                // Work orders already exist, load them
                console.log('Work order generation skipped - loading existing work orders')
                setGenerationStatus('completed')
                setWorkOrdersGenerated(true)
                await loadWorkOrders() // Load existing work orders
              } else if (data.type === 'generation_error') {
                setGenerationStatus('error')
                console.error('Work order generation error:', data.error)
              } else if (data.type === 'fallback_spec_used' || data.type === 'generation_started') {
                // Just log these for debugging
                console.log(`Work order generation: ${data.type}`)
              }
            } catch (e) {
              console.error('Error parsing streaming response:', e, 'Line:', line)
            }
          }
        }
      }
    } catch (error) {
      console.error('Error generating work orders:', error)
      setGenerationStatus('error')
    }
  }, [selectedProject, loadWorkOrders])

  // Load work orders on mount and project change
  useEffect(() => {
    loadWorkOrders()
  }, [loadWorkOrders])

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
    <GlassBackground variant="stage" className="h-full">
      <div className="flex flex-col p-6 space-y-4 h-full">
      {/* Header */}
      <div className="flex-shrink-0">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold text-yellow-400">Plan</h1>
            
            {/* View Selection Dropdown */}
            <div className="relative">
              <select
                value={activeView}
                onChange={(e) => setActiveView(e.target.value as 'work-order-enhancement' | 'task-execution')}
                className="bg-white/10 text-white border border-white/20 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-yellow-400/50"
              >
                <option value="work-order-enhancement" className="bg-gray-800">Work Order Enhancement</option>
                <option value="task-execution" className="bg-gray-800">Task Execution UI</option>
              </select>
            </div>
            
            <span className="text-sm font-medium text-white/80 px-3 py-1.5 bg-white/10 rounded-lg border border-white/20">
              {activeView === 'work-order-enhancement' ? 'Work Order Enhancement' : 'Task Execution'}
            </span>
          </div>
        </div>
        
        <p className="text-white/60">
          {activeView === 'work-order-enhancement' 
            ? 'Transform frozen tasks into comprehensive work orders with AI-powered implementation plans'
            : 'Task execution launchpad - manage and execute development tasks'
          }
        </p>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex min-h-0">
        {activeView === 'work-order-enhancement' ? (
          <WorkOrderEnhancementView
            selectedProject={selectedProject}
            workOrdersGenerated={workOrdersGenerated}
            generationStatus={generationStatus}
            onGenerateWorkOrders={handleGenerateWorkOrders}
            workOrders={workOrders}
            onWorkOrderSelect={handleWorkOrderSelect}
          />
        ) : (
          /* Kanban Board for Task Execution */
          <PanelGroup direction="horizontal">
            <Panel defaultSize={33}>
              <KanbanColumn
                title="Ready"
                tasks={tasksByStatus.ready}
                onTaskSelect={handleTaskSelect}
                isTaskBlocked={isTaskBlocked}
                getBlockingTasks={getBlockingTasks}
                getDependencyStatus={getDependencyStatus}
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
                getDependencyStatus={getDependencyStatus}
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
                getDependencyStatus={getDependencyStatus}
                onUpdateField={handleUpdateField}
                onSuggestAssignee={handleSuggestAssignee}
                onSuggestEstimate={handleSuggestEstimate}
                onSuggestAgent={handleSuggestAgent}
                onCancelTask={handleCancelTask}
              />
            </Panel>
          </PanelGroup>
        )}
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

      {/* Work Order Detail Modal */}
      <AnimatePresence>
        {showWorkOrderModal && selectedWorkOrder && (
          <WorkOrderDetailModal
            workOrder={selectedWorkOrder}
            onClose={handleCloseWorkOrderModal}
            onGenerateImplementation={handleGenerateImplementation}
          />
        )}
      </AnimatePresence>
      </div>
    </GlassBackground>
  )
}

// Kanban Column Component
interface KanbanColumnProps {
  title: string
  tasks: Task[]
  onTaskSelect: (task: Task) => void
  isTaskBlocked: (task: Task) => boolean
  getBlockingTasks: (task: Task) => string[]
  getDependencyStatus: (task: Task) => { total: number; completed: number; blocked: boolean }
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
  getDependencyStatus,
  onUpdateField,
  onSuggestAssignee,
  onSuggestEstimate,
  onSuggestAgent,
  onCancelTask
}) => {
  return (
    <div className="flex flex-col h-full bg-white/5 p-4 rounded-lg mx-2">
      <div className="flex-shrink-0 mb-4">
        <h2 className="text-xl font-semibold text-yellow-400 mb-1">{title}</h2>
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
            dependencyStatus={getDependencyStatus(task)}
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
  dependencyStatus: { total: number; completed: number; blocked: boolean }
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
  dependencyStatus,
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
        onClick={isBlocked ? undefined : onSelect}
        className={clsx(
          'transition-all',
          !isBlocked && 'cursor-pointer hover:scale-105',
          getStatusColor(),
          isBlocked && 'opacity-40 grayscale cursor-not-allowed',
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
            <div className="flex items-center justify-between mb-1">
              <div className="text-sm text-white/60">{task.task_number}</div>
              {dependencyStatus.total > 0 && (
                <div className="flex items-center text-xs">
                  <span className="text-white/40 mr-1">🔗</span>
                  <span className={clsx(
                    "font-medium",
                    dependencyStatus.blocked ? "text-orange-400" : "text-green-400"
                  )}>
                    {dependencyStatus.completed}/{dependencyStatus.total}
                  </span>
                </div>
              )}
            </div>
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

          {/* Dependency progress indicator */}
          {dependencyStatus.total > 0 && (
            <div className="mb-3 p-2 bg-white/5 rounded text-xs">
              <div className="flex items-center justify-between mb-1">
                <span className="text-white/60">Dependencies:</span>
                <span className={clsx(
                  "font-medium",
                  dependencyStatus.blocked ? "text-orange-400" : "text-green-400"
                )}>
                  {dependencyStatus.completed}/{dependencyStatus.total}
                </span>
              </div>
              <div className="bg-white/20 rounded-full h-1">
                <div 
                  className={clsx(
                    "h-1 rounded-full transition-all duration-300",
                    dependencyStatus.blocked ? "bg-orange-400" : "bg-green-400"
                  )}
                  style={{ width: `${(dependencyStatus.completed / dependencyStatus.total) * 100}%` }}
                />
              </div>
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
            <div className="mt-3 p-3 bg-red-500/30 border border-red-500/50 rounded-lg text-sm">
              <div className="flex items-center text-red-300 font-medium mb-1">
                <span className="mr-2">🔒</span>
                Blocked
              </div>
              <div className="text-red-200 text-xs">
                Waiting for: {blockingTasks.join(', ')}
              </div>
            </div>
          )}

          {/* Start button for ready tasks */}
          {task.status === 'ready' && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                if (!isBlocked) {
                  onSelect()
                }
              }}
              disabled={isBlocked}
              className={clsx(
                "w-full mt-4 py-2 font-semibold rounded-lg transition-all",
                isBlocked 
                  ? "bg-gray-600/50 text-gray-400 cursor-not-allowed" 
                  : "neon-btn neon-btn--gray hover:scale-105"
              )}
            >
              {isBlocked ? "🔒 Blocked" : "⚡ Start Task"}
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
          <h2 className="text-xl font-bold text-yellow-400">Plan • Prepare Agent Run</h2>
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
          <h3 className="text-lg font-semibold text-yellow-400 mb-4 flex items-center">
            <span className="bg-yellow-500/20 text-yellow-400 rounded-full w-6 h-6 flex items-center justify-center text-sm mr-2">1</span>
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
          <h3 className="text-lg font-semibold text-yellow-400 mb-4 flex items-center">
            <span className="bg-yellow-500/20 text-yellow-400 rounded-full w-6 h-6 flex items-center justify-center text-sm mr-2">2</span>
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
          <h3 className="text-lg font-semibold text-yellow-400 mb-4 flex items-center">
            <span className="bg-yellow-500/20 text-yellow-400 rounded-full w-6 h-6 flex items-center justify-center text-sm mr-2">3</span>
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

// Work Order Enhancement View Component
interface WorkOrderEnhancementViewProps {
  selectedProject: string | null
  workOrdersGenerated: boolean
  generationStatus: 'idle' | 'generating' | 'completed' | 'error'
  onGenerateWorkOrders: () => void
  workOrders: any[]
  onWorkOrderSelect: (workOrder: any) => void
}

const WorkOrderEnhancementView: React.FC<WorkOrderEnhancementViewProps> = ({
  selectedProject,
  workOrdersGenerated,
  generationStatus,
  onGenerateWorkOrders,
  workOrders,
  onWorkOrderSelect
}) => {
  // Table state
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [selectedStatus, setSelectedStatus] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedWorkOrder, setSelectedWorkOrder] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'description' | 'implementation' | 'blueprint' | 'prd'>('description');

  if (!selectedProject) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-white/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-white/40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-white mb-2">No Project Selected</h3>
          <p className="text-white/60">Select a project to generate work orders</p>
        </div>
      </div>
    )
  }

  if (generationStatus === 'idle' && workOrders.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="w-20 h-20 bg-gradient-to-br from-yellow-400/20 to-orange-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-10 h-10 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <h3 className="text-xl font-semibold text-white mb-3">Ready to Generate Work Orders</h3>
          <p className="text-white/60 mb-6 leading-relaxed">
            Transform your tasks into detailed, AI-enhanced work orders with implementation guidance, 
            codebase analysis, and specific file recommendations.
          </p>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onGenerateWorkOrders}
            className="neon-btn neon-btn--yellow px-8 py-3 text-lg font-medium"
          >
            ⚡ Create with AI
          </motion.button>
        </div>
      </div>
    )
  }

  if (generationStatus === 'generating') {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-yellow-400/20 border-t-yellow-400 rounded-full animate-spin mx-auto mb-4"></div>
          <h3 className="text-lg font-medium text-white mb-2">Generating Work Orders</h3>
          <p className="text-white/60">Analyzing tasks and creating enhanced work orders...</p>
        </div>
      </div>
    )
  }

  if (generationStatus === 'error') {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-white mb-2">Generation Failed</h3>
          <p className="text-white/60 mb-4">Failed to generate work orders. Please try again.</p>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onGenerateWorkOrders}
            className="neon-btn neon-btn--gray px-6 py-2"
          >
            🔄 Retry
          </motion.button>
        </div>
      </div>
    )
  }

  if (workOrders.length > 0) {
    // Filter and pagination logic
    const filteredWorkOrders = workOrders.filter(workOrder => {
      const matchesSearch = workOrder.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           workOrder.description?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           workOrder.purpose?.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesCategory = selectedCategory === 'all' || workOrder.category === selectedCategory;
      const matchesStatus = selectedStatus === 'all' || workOrder.status === selectedStatus;
      return matchesSearch && matchesCategory && matchesStatus;
    });

    const itemsPerPage = 10;
    const totalPages = Math.ceil(filteredWorkOrders.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const paginatedWorkOrders = filteredWorkOrders.slice(startIndex, startIndex + itemsPerPage);

    return (
      <div className="flex-1 h-full">
        <PanelGroup direction="horizontal">
          {/* Left Panel - Work Orders Table */}
          <Panel defaultSize={60} minSize={40}>
            <div className="h-full flex flex-col bg-black/20 backdrop-blur-sm rounded-lg border border-white/10">
              {/* Header with Search and Filters */}
              <div className="flex-shrink-0 p-4 border-b border-gray-700/30">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl font-semibold text-white">Work Orders</h3>
                  <div className="flex items-center space-x-4">
                    <motion.button
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={onGenerateWorkOrders}
                      className="neon-btn neon-btn--blue px-4 py-2 text-sm"
                    >
                      🔄 Regenerate
                    </motion.button>
                  </div>
                </div>

                {/* Search and Filters */}
                <div className="flex space-x-4">
                  <div className="flex-1">
                    <input
                      type="text"
                      placeholder="Search work orders..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="w-full px-3 py-2 bg-black/30 border border-white/20 rounded-lg text-white placeholder-white/50 focus:outline-none focus:border-yellow-400/50"
                    />
                  </div>
                  <select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="px-3 py-2 bg-black/30 border border-white/20 rounded-lg text-white focus:outline-none focus:border-yellow-400/50"
                  >
                    <option value="all">All Categories</option>
                    <option value="Data Model">Data Model</option>
                    <option value="Implementation">Implementation</option>
                    <option value="Testing">Testing</option>
                  </select>
                  <select
                    value={selectedStatus}
                    onChange={(e) => setSelectedStatus(e.target.value)}
                    className="px-3 py-2 bg-black/30 border border-white/20 rounded-lg text-white focus:outline-none focus:border-yellow-400/50"
                  >
                    <option value="all">All Statuses</option>
                    <option value="ready">Ready</option>
                    <option value="backlog">Backlog</option>
                    <option value="in-progress">In Progress</option>
                  </select>
                </div>
              </div>

              {/* Table */}
              <div className="flex-1 overflow-auto">
                <table className="w-full">
                  <thead className="sticky top-0 bg-gray-800/50 backdrop-blur-sm">
                    <tr className="border-b border-gray-700/30">
                      <th className="px-4 py-3 text-left text-sm font-medium text-white/70">ID</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-white/70">Title & Related Idea</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-white/70">Category</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-white/70">Assignee</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-white/70">Status</th>
                      <th className="px-4 py-3 text-left text-sm font-medium text-white/70">Implementation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedWorkOrders.map((workOrder, index) => (
                      <tr
                        key={workOrder.id}
                        onClick={() => setSelectedWorkOrder(workOrder)}
                        className={clsx(
                          "cursor-pointer transition-colors border-b border-gray-800/30 hover:bg-white/5",
                          selectedWorkOrder?.id === workOrder.id && "bg-yellow-400/10"
                        )}
                      >
                        <td className="px-4 py-4 text-sm font-mono text-white/80">WO-{workOrder.task_number}</td>
                        <td className="px-4 py-4">
                          <div>
                            <div className="font-medium text-white">{workOrder.title}</div>
                            <div className="text-sm text-white/50">💡 {workOrder.related_idea || 'Core Functionality'}</div>
                          </div>
                        </td>
                        <td className="px-4 py-4 text-sm text-purple-400">{workOrder.category || 'Implementation'}</td>
                        <td className="px-4 py-4 text-sm text-white/70">{workOrder.assignee || 'Unassigned'}</td>
                        <td className="px-4 py-4">
                          <span className={clsx(
                            "px-2 py-1 rounded text-xs font-medium",
                            workOrder.status === 'ready' ? 'bg-green-500/20 text-green-400' :
                            workOrder.status === 'backlog' ? 'bg-yellow-500/20 text-yellow-400' :
                            'bg-gray-500/20 text-gray-400'
                          )}>
                            {(workOrder.status || 'ready').toUpperCase()}
                          </span>
                        </td>
                        <td className="px-4 py-4">
                          {workOrder.implementation_plan ? (
                            <span className="text-green-400 text-xs">✓ Ready</span>
                          ) : (
                            <span className="text-yellow-400 text-xs">⚠ Needs Plan</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="flex-shrink-0 px-4 py-3 border-t border-gray-700/30 flex items-center justify-between">
                <div className="text-sm text-white/60">
                  Showing {startIndex + 1} to {Math.min(startIndex + itemsPerPage, filteredWorkOrders.length)} of {filteredWorkOrders.length}
                </div>
                <div className="flex space-x-2">
                  <button
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                    className="px-3 py-1 bg-black/30 border border-white/20 rounded text-sm text-white disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <span className="px-3 py-1 text-sm text-white">
                    {currentPage} of {totalPages}
                  </span>
                  <button
                    onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                    disabled={currentPage === totalPages}
                    className="px-3 py-1 bg-black/30 border border-white/20 rounded text-sm text-white disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            </div>
          </Panel>

          <PanelResizeHandle className="w-2 bg-gray-700/30 hover:bg-yellow-400/30 transition-colors" />

          {/* Right Panel - Work Order Details */}
          <Panel defaultSize={40} minSize={30}>
            {selectedWorkOrder ? (
              <div className="h-full flex flex-col bg-black/20 backdrop-blur-sm rounded-lg border border-white/10">
                {/* Header */}
                <div className="flex-shrink-0 px-6 py-4 border-b border-gray-700/30">
                  <div className="flex items-center justify-between">
                    <button
                      onClick={() => setSelectedWorkOrder(null)}
                      className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                    >
                      <svg className="w-5 h-5 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                  <p className="text-lg text-white font-medium">{selectedWorkOrder.title}</p>
                  <div className="flex items-center space-x-4 mt-2 text-sm text-white/60">
                    <span>💡 Related to: {selectedWorkOrder.related_idea || 'Core Functionality'}</span>
                    <span>👤 {selectedWorkOrder.assignee || 'Unassigned'}</span>
                    <span className={clsx(
                      "px-2 py-1 rounded text-xs font-medium",
                      selectedWorkOrder.status === 'ready' ? 'bg-green-500/20 text-green-400' :
                      selectedWorkOrder.status === 'backlog' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-gray-500/20 text-gray-400'
                    )}>
                      {(selectedWorkOrder.status || 'ready').toUpperCase()}
                    </span>
                  </div>
                </div>

                {/* Tab Navigation */}
                <div className="flex-shrink-0 px-6 bg-gray-800/30 border-b border-gray-700/30">
                  <div className="flex space-x-8">
                    {[
                      { id: 'description', label: 'Description', icon: '📝' },
                      { id: 'implementation', label: 'Implementation', icon: '🛠️' },
                      { id: 'blueprint', label: 'Blueprint', icon: '📋' },
                      { id: 'prd', label: 'PRD', icon: '📄' }
                    ].map((tab) => (
                      <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id as any)}
                        className={clsx(
                          'py-4 px-2 border-b-2 font-medium text-sm transition-colors',
                          activeTab === tab.id
                            ? 'border-yellow-400 text-yellow-400'
                            : 'border-transparent text-white/60 hover:text-white hover:border-white/30'
                        )}
                      >
                        {tab.icon} {tab.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Tab Content */}
                <div className="flex-1 overflow-auto p-6 space-y-6">
                  {activeTab === 'description' && (
                    <>
                      <div>
                        <h3 className="text-lg font-semibold text-white mb-3">Purpose</h3>
                        <p className="text-white/80 leading-relaxed">
                          {selectedWorkOrder.purpose || selectedWorkOrder.description || 'No description available.'}
                        </p>
                      </div>
                      
                      {selectedWorkOrder.requirements && selectedWorkOrder.requirements.length > 0 && (
                        <div>
                          <h3 className="text-lg font-semibold text-white mb-3">Requirements</h3>
                          <ul className="space-y-2">
                            {selectedWorkOrder.requirements.map((req: string, index: number) => (
                              <li key={index} className="text-white/80 flex items-start space-x-2">
                                <span className="text-yellow-400 mt-1">•</span>
                                <span>{req}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </>
                  )}
                  
                  {activeTab === 'implementation' && (
                    <div>
                      <h3 className="text-lg font-semibold text-white mb-3">Implementation Plan</h3>
                      <div className="prose prose-invert max-w-none">
                        <pre className="whitespace-pre-wrap text-white/80 text-sm leading-relaxed">
                          {selectedWorkOrder.implementation_plan || 'No implementation plan available yet.'}
                        </pre>
                      </div>
                    </div>
                  )}
                  
                  {activeTab === 'blueprint' && (
                    <div>
                      <h3 className="text-lg font-semibold text-white mb-3">Technical Blueprint</h3>
                      <div className="prose prose-invert max-w-none">
                        <pre className="whitespace-pre-wrap text-white/80 text-sm leading-relaxed">
                          {selectedWorkOrder.blueprint || 'Technical blueprint will be generated based on the implementation plan.'}
                        </pre>
                      </div>
                    </div>
                  )}
                  
                  {activeTab === 'prd' && (
                    <div>
                      <h3 className="text-lg font-semibold text-white mb-3">Product Requirements</h3>
                      <div className="prose prose-invert max-w-none">
                        <pre className="whitespace-pre-wrap text-white/80 text-sm leading-relaxed">
                          {selectedWorkOrder.prd || 'Product requirements document will be generated from the work order context.'}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center bg-black/20 backdrop-blur-sm rounded-lg border border-white/10">
                <div className="text-center text-white/50">
                  <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p>Select a work order to view details</p>
                </div>
              </div>
            )}
          </Panel>
        </PanelGroup>
      </div>
    )
  }

  // Default view: "Create with AI" button
    return (
      <div className="flex-1 flex items-center justify-center">
      <div className="text-center max-w-md">
        <div className="w-20 h-20 bg-gradient-to-br from-yellow-400/20 to-orange-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
          <svg className="w-10 h-10 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
        <h3 className="text-xl font-semibold text-white mb-3">Ready to Generate Work Orders</h3>
        <p className="text-white/60 mb-6 leading-relaxed">
          Transform your tasks into detailed, AI-enhanced work orders with implementation guidance, 
          codebase analysis, and specific file recommendations.
        </p>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={onGenerateWorkOrders}
          className="neon-btn neon-btn--yellow px-8 py-3 text-lg font-medium"
          >
          ⚡ Create with AI
          </motion.button>
        </div>
      </div>
    )
  }

// Work Order Detail Modal Component
interface WorkOrderDetailModalProps {
  workOrder: any
  onClose: () => void
  onGenerateImplementation?: (workOrderId: string) => void
}

const WorkOrderDetailModal: React.FC<WorkOrderDetailModalProps> = ({
  workOrder,
  onClose,
  onGenerateImplementation
}) => {
  const [activeTab, setActiveTab] = useState<'description' | 'implementation' | 'blueprint' | 'prd'>('description')
  const [generatingPlan, setGeneratingPlan] = useState(false)

  const handleGenerateImplementation = async () => {
    if (!onGenerateImplementation) return
    setGeneratingPlan(true)
    try {
      await onGenerateImplementation(workOrder.id)
    } finally {
      setGeneratingPlan(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        className="w-full max-w-6xl h-[90vh] bg-gray-900/95 backdrop-blur-lg border border-gray-700/50 rounded-2xl shadow-2xl flex flex-col"
      >
        {/* Header */}
        <div className="flex-shrink-0 p-6 border-b border-gray-700/50 bg-gray-800/50">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-4">
              <h2 className="text-2xl font-bold text-yellow-400">Work Order Details</h2>
              <div className="px-3 py-1 rounded text-sm font-medium bg-blue-500/20 text-blue-400">
                WO-{workOrder.task_number || '001'}
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white p-2 rounded-lg hover:bg-gray-700/50 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <p className="text-lg text-white font-medium">{workOrder.title}</p>
          <div className="flex items-center space-x-4 mt-2 text-sm text-white/60">
            <span>💡 Related to: {workOrder.related_idea || 'Core Functionality'}</span>
            <span>👤 {workOrder.assignee || 'Unassigned'}</span>
            <span className={`px-2 py-1 rounded text-xs font-medium ${
              workOrder.status === 'ready' ? 'bg-green-500/20 text-green-400' :
              workOrder.status === 'backlog' ? 'bg-yellow-500/20 text-yellow-400' :
              'bg-gray-500/20 text-gray-400'
            }`}>
              {(workOrder.status || 'ready').toUpperCase()}
            </span>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex-shrink-0 px-6 bg-gray-800/30 border-b border-gray-700/30">
          <div className="flex space-x-8">
            {[
              { id: 'description', label: 'Description', icon: '📝' },
              { id: 'implementation', label: 'Implementation', icon: '🛠️' },
              { id: 'blueprint', label: 'Blueprint', icon: '📋' },
              { id: 'prd', label: 'PRD', icon: '📄' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={clsx(
                  'py-4 px-2 border-b-2 font-medium text-sm transition-colors',
                  activeTab === tab.id
                    ? 'border-yellow-400 text-yellow-400'
                    : 'border-transparent text-white/60 hover:text-white hover:border-white/30'
                )}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-hidden">
          {activeTab === 'description' && (
            <div className="h-full overflow-y-auto p-6 space-y-6">
              {/* Purpose */}
              <div>
                <h3 className="text-lg font-semibold text-white mb-3">Purpose</h3>
                <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/30">
                  <p className="text-white/80 leading-relaxed">
                    {workOrder.purpose || workOrder.description || 'No description available.'}
                  </p>
                </div>
              </div>

              {/* Requirements */}
              <div>
                <h3 className="text-lg font-semibold text-white mb-3">Requirements</h3>
                <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/30">
                  {workOrder.requirements && workOrder.requirements.length > 0 ? (
                    <ul className="space-y-2">
                      {workOrder.requirements.map((req: string, index: number) => (
                        <li key={index} className="flex items-start space-x-2">
                          <span className="text-green-400 mt-1">✓</span>
                          <span className="text-white/80">{req}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-white/60">No specific requirements defined.</p>
                  )}
                </div>
              </div>

              {/* Acceptance Criteria */}
              <div>
                <h3 className="text-lg font-semibold text-white mb-3">Acceptance Criteria</h3>
                <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/30">
                  {workOrder.acceptance_criteria && workOrder.acceptance_criteria.length > 0 ? (
                    <ul className="space-y-2">
                      {workOrder.acceptance_criteria.map((criteria: string, index: number) => (
                        <li key={index} className="flex items-start space-x-2">
                          <span className="text-blue-400 mt-1">🎯</span>
                          <span className="text-white/80">{criteria}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-white/60">No acceptance criteria defined.</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'implementation' && (
            <div className="h-full overflow-y-auto p-6">
              {workOrder.implementation_plan ? (
                <div className="space-y-6">
                  {/* Plan Description */}
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-3">Plan Description</h3>
                    <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/30">
                      <p className="text-white/80 leading-relaxed">
                        {workOrder.implementation_plan.description}
                      </p>
                    </div>
                  </div>

                  {/* Approach Summary */}
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-3">Approach Summary</h3>
                    <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/30">
                      <p className="text-white/80 leading-relaxed">
                        {workOrder.implementation_plan.approach_summary}
                      </p>
                    </div>
                  </div>

                  {/* Goals */}
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-3">Goals</h3>
                    <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/30">
                      <ul className="space-y-2">
                        {(workOrder.implementation_plan.goals || []).map((goal: string, index: number) => (
                          <li key={index} className="flex items-start space-x-2">
                            <span className="text-green-400 mt-1">🎯</span>
                            <span className="text-white/80">{goal}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {/* Strategy */}
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-3">Strategy</h3>
                    <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/30">
                      <p className="text-white/80 leading-relaxed">
                        {workOrder.implementation_plan.strategy}
                      </p>
                    </div>
                  </div>

                  {/* Dependencies */}
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-3">Dependencies</h3>
                    <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/30">
                      {workOrder.implementation_plan.dependencies && workOrder.implementation_plan.dependencies.length > 0 ? (
                        <ul className="space-y-2">
                          {workOrder.implementation_plan.dependencies.map((dep: string, index: number) => (
                            <li key={index} className="flex items-start space-x-2">
                              <span className="text-orange-400 mt-1">⚠️</span>
                              <span className="text-white/80">{dep}</span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-white/60">No dependencies identified.</p>
                      )}
                    </div>
                  </div>

                  {/* Implementation Files */}
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-3">Implementation Files</h3>
                    <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/30">
                      {workOrder.implementation_plan.implementation_files && workOrder.implementation_plan.implementation_files.length > 0 ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                          {workOrder.implementation_plan.implementation_files.map((file: string, index: number) => (
                            <div key={index} className="flex items-center space-x-2 bg-gray-900/50 rounded p-2">
                              <span className="text-blue-400">📁</span>
                              <code className="text-sm text-green-400 font-mono">{file}</code>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-white/60">No specific files identified.</p>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full space-y-6">
                  <div className="text-center">
                    <div className="w-20 h-20 bg-yellow-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                      <svg className="w-10 h-10 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                      </svg>
                    </div>
                    <h3 className="text-xl font-semibold text-white mb-2">No Implementation Plan</h3>
                    <p className="text-white/60 mb-6">
                      Generate a comprehensive, codebase-aware implementation plan for this work order.
                    </p>
                  </div>
                  <button
                    onClick={handleGenerateImplementation}
                    disabled={generatingPlan}
                    className={clsx(
                      'neon-btn px-8 py-3 text-lg font-medium',
                      generatingPlan ? 'neon-btn--disabled' : 'neon-btn--yellow'
                    )}
                  >
                    {generatingPlan ? (
                      <div className="flex items-center space-x-2">
                        <div className="w-5 h-5 border-2 border-yellow-300/30 border-t-yellow-300 rounded-full animate-spin"></div>
                        <span>Generating...</span>
                      </div>
                    ) : (
                      '🛠️ Generate with AI'
                    )}
                  </button>
                </div>
              )}
            </div>
          )}

          {activeTab === 'blueprint' && (
            <div className="h-full overflow-y-auto p-6">
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">Blueprint Section</h3>
                <p className="text-white/60">
                  Architecture blueprints and technical specifications will be displayed here.
                </p>
                <button className="mt-6 neon-btn neon-btn--blue px-6 py-2">
                  Generate Blueprint
                </button>
              </div>
            </div>
          )}

          {activeTab === 'prd' && (
            <div className="h-full overflow-y-auto p-6">
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-purple-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">PRD Section</h3>
                <p className="text-white/60">
                  Related Product Requirements Document sections and user stories will be displayed here.
                </p>
                <button className="mt-6 neon-btn neon-btn--purple px-6 py-2">
                  Link PRD Sections
                </button>
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  )
}

export default PlanStage