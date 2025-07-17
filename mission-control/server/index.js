/**
 * Mission Control Backend Server
 * 
 * This is a simple Express server that provides the API endpoints
 * for Mission Control. It includes mock data and basic functionality
 * to demonstrate the complete system.
 * 
 * Why this server exists:
 * - Provides API endpoints as defined in the spec
 * - Serves mock data for development and testing
 * - Handles WebSocket connections for real-time updates
 * - Integrates with existing Software Factory backend
 * 
 * For AI agents: This is the backend server for Mission Control.
 * It provides all the API endpoints needed by the frontend.
 */

const express = require('express')
const cors = require('cors')
const http = require('http')
const socketIo = require('socket.io')
const path = require('path')

const app = express()
const server = http.createServer(app)
const io = socketIo(server, {
  cors: {
    origin: process.env.NODE_ENV === 'production' ? false : ['http://localhost:3000', 'http://localhost:5173', 'http://localhost:8009'],
    methods: ['GET', 'POST'],
  },
})

// Middleware
app.use(cors())
app.use(express.json())
app.use(express.static(path.join(__dirname, '..', 'dist')))

const dataStore = require('./dataStore')
// Use live store instead of static mocks
const mockProjects = dataStore.projects

const mockFeedItems = dataStore.feedItems

const mockConversations = dataStore.conversations

// API Routes

// Health check
app.get('/api/health', (req, res) => {
  res.json({
    success: true,
    data: {
      status: 'healthy',
      timestamp: new Date().toISOString(),
    },
    timestamp: new Date().toISOString(),
    version: '1.0.0',
  })
})

// Projects endpoints
app.get('/api/projects', (req, res) => {
  res.json({
    success: true,
    data: mockProjects,
    timestamp: new Date().toISOString(),
    version: '1.0.0',
  })
})

app.get('/api/projects/:id', (req, res) => {
  const project = mockProjects.find(p => p.id === req.params.id)
  if (!project) {
    return res.status(404).json({
      success: false,
      error: 'Project not found',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    })
  }
  
  res.json({
    success: true,
    data: project,
    timestamp: new Date().toISOString(),
    version: '1.0.0',
  })
})

// Serve system map JSON for a project
app.get('/api/projects/:id/system-map', (req, res) => {
  const project = mockProjects.find(p => p.id === req.params.id)
  if (!project) {
    return res.status(404).json({ success: false, error: 'Project not found' })
  }

  if (!project.metadata?.systemMapPath) {
    return res.status(404).json({ success: false, error: 'System map not generated yet' })
  }

  try {
    const mapJson = require(project.metadata.systemMapPath)
    return res.json({ success: true, data: mapJson })
  } catch (e) {
    console.error('Failed to load system map', e)
    return res.status(500).json({ success: false, error: 'Failed to load map' })
  }
})

// Add new project (from Add Project Modal)
app.post('/api/projects', async (req, res) => {
  try {
    const { name, repoUrl } = req.body
    
    if (!name || !repoUrl) {
      return res.status(400).json({
        success: false,
        error: 'Project name and repository URL are required',
        timestamp: new Date().toISOString(),
        version: '1.0.0',
      })
    }
    
    // Generate new project ID
    const projectId = `project_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    
    // Create new project
    const newProject = {
      id: projectId,
      name,
      description: `Project created from ${repoUrl}`,
      repoUrl,
      health: 'amber', // Initially amber while indexing
      unreadCount: 0,
      lastActivity: new Date().toISOString(),
      createdAt: new Date().toISOString(),
      systemMapStatus: 'in_progress',
      metadata: {
        repoUrl,
        systemMapGenerated: false,
        docsUploaded: false,
      }
    }
    
    // Add to mock projects
    mockProjects.push(newProject)
    dataStore.addProject(newProject)
    
    // Emit project creation event for real-time ingestion
    io.emit('project.created', {
      projectId,
      repoUrl,
      name,
    })
    
    console.log(`New project created: ${name} (${projectId})`)
    console.log(`Repository: ${repoUrl}`)
    console.log(`Ingestion agent should now process this project...`)
    
    res.json({
      success: true,
      data: newProject,
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    })
  } catch (error) {
    console.error('Error creating project:', error)
    res.status(500).json({
      success: false,
      error: 'Failed to create project',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    })
  }
})

// Delete project
app.delete('/api/projects/:id', (req, res) => {
  const projectId = req.params.id
  const idx = mockProjects.findIndex(p => p.id === projectId)
  if (idx === -1) {
    return res.status(404).json({ success: false, error: 'Project not found' })
  }

  const [removed] = mockProjects.splice(idx, 1)
  dataStore.removeProject(projectId)

  // Emit event so UI can update
  io.emit('project.deleted', { projectId })

  res.json({ success: true, data: removed, timestamp: new Date().toISOString() })
})

// Upload project documents
app.post('/api/projects/docs', async (req, res) => {
  try {
    const { projectName } = req.body
    
    if (!projectName) {
      return res.status(400).json({
        success: false,
        error: 'Project name is required',
        timestamp: new Date().toISOString(),
        version: '1.0.0',
      })
    }
    
    // Find project by name
    const project = mockProjects.find(p => p.name === projectName)
    if (!project) {
      return res.status(404).json({
        success: false,
        error: 'Project not found',
        timestamp: new Date().toISOString(),
        version: '1.0.0',
      })
    }
    
    // In a real implementation, you would:
    // 1. Process uploaded files from req.files
    // 2. Store files in a file system or cloud storage
    // 3. Index documents for AI search
    // 4. Trigger document ingestion process
    
    // For now, we'll just simulate the process
    project.metadata.docsUploaded = true
    project.metadata.docCount = Object.keys(req.body).filter(key => key.startsWith('doc_')).length
    
    // Emit document upload event
    io.emit('project.docs.uploaded', {
      projectId: project.id,
      docCount: project.metadata.docCount,
    })
    
    console.log(`Documents uploaded for project: ${projectName}`)
    console.log(`Document count: ${project.metadata.docCount}`)
    console.log(`Ingestion agent should now process these documents...`)
    
    res.json({
      success: true,
      data: {
        projectId: project.id,
        docCount: project.metadata.docCount,
      },
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    })
  } catch (error) {
    console.error('Error uploading documents:', error)
    res.status(500).json({
      success: false,
      error: 'Failed to upload documents',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    })
  }
})

// Feed endpoints
app.get('/api/feed', (req, res) => {
  const { projectId, severity, unread, limit = 20, cursor } = req.query
  
  let filtered = mockFeedItems
  
  if (projectId) {
    filtered = filtered.filter(item => item.projectId === projectId)
  }
  
  if (severity) {
    filtered = filtered.filter(item => item.severity === severity)
  }
  
  if (unread === 'true') {
    filtered = filtered.filter(item => item.unread)
  }
  
  // Sort by creation time (newest first)
  filtered.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())
  
  const limitNum = parseInt(limit)
  const items = filtered.slice(0, limitNum)
  
  res.json({
    success: true,
    data: {
      items,
      total: filtered.length,
      page: 1,
      pageSize: limitNum,
      hasMore: filtered.length > limitNum,
    },
    timestamp: new Date().toISOString(),
    version: '1.0.0',
  })
})

app.post('/api/feed/:id/mark-read', (req, res) => {
  const feedItem = mockFeedItems.find(item => item.id === req.params.id)
  if (!feedItem) {
    return res.status(404).json({
      success: false,
      error: 'Feed item not found',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    })
  }
  
  feedItem.unread = false
  
  // Update project unread count
  const project = mockProjects.find(p => p.id === feedItem.projectId)
  if (project && project.unreadCount > 0) {
    project.unreadCount -= 1
  }
  
  // Emit real-time update
  io.emit('feed.update', {
    feedItemId: feedItem.id,
    fields: { unread: false },
  })
  
  res.json({
    success: true,
    timestamp: new Date().toISOString(),
    version: '1.0.0',
  })
})

app.post('/api/feed/:id/action', (req, res) => {
  const { action } = req.body
  const feedItem = mockFeedItems.find(item => item.id === req.params.id)
  
  if (!feedItem) {
    return res.status(404).json({
      success: false,
      error: 'Feed item not found',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    })
  }
  
  console.log(`Performing action "${action}" on feed item ${req.params.id}`)
  
  // Simulate action processing
  setTimeout(() => {
    io.emit('feed.update', {
      feedItemId: feedItem.id,
      fields: { 
        summary: `Action "${action}" completed`,
        updatedAt: new Date().toISOString(),
      },
    })
  }, 1000)
  
  res.json({
    success: true,
    timestamp: new Date().toISOString(),
    version: '1.0.0',
  })
})

// External import: allow other services (ex: Slack bridge) to inject feed items
app.post('/api/feed/import', (req, res) => {
  try {
    const item = req.body
    if (!item || !item.id) {
      return res.status(400).json({ success: false, error: 'Invalid feed item' })
    }

    dataStore.addFeedItem(item)

    // Broadcast real-time event to connected clients
    io.emit('feed.new', { feedItem: item })

    res.json({ success: true })
  } catch (err) {
    console.error('Import feed item error:', err)
    res.status(500).json({ success: false, error: 'Server error' })
  }
})

// Conversation endpoints
app.get('/api/conversation/:feedItemId', (req, res) => {
  const conversation = mockConversations[req.params.feedItemId]
  
  if (!conversation) {
    return res.status(404).json({
      success: false,
      error: 'Conversation not found',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    })
  }
  
  res.json({
    success: true,
    data: conversation,
    timestamp: new Date().toISOString(),
    version: '1.0.0',
  })
})

app.post('/api/conversation/:feedItemId/prompt', (req, res) => {
  const { prompt } = req.body
  const conversation = mockConversations[req.params.feedItemId]
  
  if (!conversation) {
    return res.status(404).json({
      success: false,
      error: 'Conversation not found',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    })
  }
  
  console.log(`Received prompt for ${req.params.feedItemId}: ${prompt}`)
  
  // Simulate AI response
  setTimeout(() => {
    const response = {
      type: 'llm_suggestion',
      command: prompt,
      explanation: `Processed command: ${prompt}`,
      confidence: 0.88,
    }
    
    conversation.blocks.push(response)
    
    io.emit('conversation.update', {
      feedItemId: req.params.feedItemId,
      newBlock: response,
    })
  }, 2000)
  
  res.json({
    success: true,
    timestamp: new Date().toISOString(),
    version: '1.0.0',
  })
})

// Channel mapping endpoints
app.get('/api/channel-mapping/:channelId', (req, res) => {
  const projectId = dataStore.getProjectForChannel(req.params.channelId)
  if (!projectId) {
    return res.status(404).json({
      success: false,
      error: 'Channel mapping not found',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    })
  }
  
  res.json({
    success: true,
    data: { projectId },
    timestamp: new Date().toISOString(),
    version: '1.0.0',
  })
})

app.post('/api/channel-mapping', (req, res) => {
  const { channelId, projectId } = req.body
  
  if (!channelId || !projectId) {
    return res.status(400).json({
      success: false,
      error: 'Channel ID and Project ID are required',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    })
  }
  
  dataStore.addChannelMapping(channelId, projectId)
  
  res.json({
    success: true,
    timestamp: new Date().toISOString(),
    version: '1.0.0',
  })
})

// Stage management
app.post('/api/idea/:id/move-stage', async (req, res) => {
  const { targetStage, fromStage, projectId } = req.body
  const itemId = req.params.id
  
  if (!targetStage || !projectId) {
    return res.status(400).json({
      success: false,
      error: 'Target stage and project ID are required',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    })
  }
  
  try {
    // Move item to new stage
    dataStore.moveItemToStage(itemId, fromStage, targetStage, projectId)
    
    // If moving to Define stage, create a product brief
    if (targetStage === 'define') {
      const feedItem = dataStore.feedItems.find(item => item.id === itemId)
      if (feedItem) {
        // Auto-generate enhanced brief content using LLM
        const briefData = await generateProductBriefContent(feedItem)
        
        const brief = dataStore.createProductBrief(itemId, projectId, briefData)
        
        // Update the feed item to include stage metadata
        dataStore.updateFeedItem(itemId, {
          metadata: {
            ...feedItem.metadata,
            stage: 'define'
          }
        })
        
        // Emit real-time update
        io.emit('stage.moved', {
          itemId,
          fromStage,
          toStage: targetStage,
          projectId,
          brief
        })
        
        return res.json({
          success: true,
          data: { brief },
          timestamp: new Date().toISOString(),
          version: '1.0.0',
        })
      }
    }
    
    // Emit real-time update
    io.emit('stage.moved', {
      itemId,
      fromStage,
      toStage: targetStage,
      projectId
    })
    
    res.json({
      success: true,
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    })
  } catch (error) {
    console.error('Error moving item to stage:', error)
    res.status(500).json({
      success: false,
      error: 'Failed to move item to stage',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    })
  }
})

// Product Brief endpoints
app.get('/api/product-brief/:briefId', (req, res) => {
  const brief = dataStore.getProductBrief(req.params.briefId)
  if (!brief) {
    return res.status(404).json({
      success: false,
      error: 'Product brief not found',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    })
  }
  
  res.json({
    success: true,
    data: brief,
    timestamp: new Date().toISOString(),
    version: '1.0.0',
  })
})

app.put('/api/product-brief/:briefId', (req, res) => {
  const { briefId } = req.params
  const updates = req.body
  
  const brief = dataStore.getProductBrief(briefId)
  if (!brief) {
    return res.status(404).json({
      success: false,
      error: 'Product brief not found',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    })
  }
  
  dataStore.updateProductBrief(briefId, updates)
  
  // Emit real-time update
  io.emit('brief.updated', {
    briefId,
    updates
  })
  
  res.json({
    success: true,
    timestamp: new Date().toISOString(),
    version: '1.0.0',
  })
})

app.post('/api/product-brief/:briefId/freeze', (req, res) => {
  const { briefId } = req.params
  
  const brief = dataStore.getProductBrief(briefId)
  if (!brief) {
    return res.status(404).json({
      success: false,
      error: 'Product brief not found',
      timestamp: new Date().toISOString(),
      version: '1.0.0',
    })
  }
  
  dataStore.freezeProductBrief(briefId)
  
  // Emit real-time update
  io.emit('brief.frozen', {
    briefId,
    frozenAt: new Date().toISOString()
  })
  
  res.json({
    success: true,
    timestamp: new Date().toISOString(),
    version: '1.0.0',
  })
})

// Get stage data for a project
app.get('/api/project/:projectId/stages', (req, res) => {
  const { projectId } = req.params
  const stages = dataStore.stages[projectId] || {
    think: [], define: [], plan: [], build: [], validate: []
  }
  
  res.json({
    success: true,
    data: stages,
    timestamp: new Date().toISOString(),
    version: '1.0.0',
  })
})

// WebSocket connection handling
io.on('connection', (socket) => {
  console.log('Client connected:', socket.id)
  
  socket.on('disconnect', () => {
    console.log('Client disconnected:', socket.id)
  })
})

// Serve React app for all other routes
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'dist', 'index.html'))
})

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Server error:', err)
  res.status(500).json({
    success: false,
    error: 'Internal server error',
    timestamp: new Date().toISOString(),
    version: '1.0.0',
  })
})

// Start server (fixed port expected by Vite proxy and landing page)
const PORT = process.env.PORT || 5001
server.listen(PORT, () => {
  console.log(`Mission Control server running on port ${PORT}`)
  console.log(`WebSocket server ready for real-time updates`)
})

// AI-powered Product Brief generation
async function generateProductBriefContent(feedItem) {
  // This is where we'd integrate with your AI providers
  // For now, we'll provide intelligent starter content
  
  const title = feedItem.title
  const summary = feedItem.summary || feedItem.title
  
  // Generate starter content based on the idea
  const briefData = {
    problemStatement: summary,
    successMetrics: [
      'User engagement increases by 20%',
      'Feature adoption rate above 60%'
    ],
    risks: [
      'Technical complexity may delay delivery',
      'User learning curve for new feature'
    ],
    competitiveAnalysis: `Research needed on how competitors handle similar features related to: ${title}`,
    userStories: [
      {
        id: 'story-1',
        title: `As a user, I want ${title.toLowerCase()}`,
        description: `User story derived from: ${summary}`,
        acceptanceCriteria: [
          'Feature is discoverable in the UI',
          'Feature works on all supported devices',
          'Feature has proper error handling'
        ],
        priority: 'high',
        status: 'draft'
      }
    ],
    progress: 0.3 // 30% complete with this starter content
  }
  
  return briefData
}

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('Received SIGTERM, shutting down gracefully')
  server.close(() => {
    console.log('Server closed')
    process.exit(0)
  })
})

process.on('SIGINT', () => {
  console.log('Received SIGINT, shutting down gracefully')
  server.close(() => {
    console.log('Server closed')
    process.exit(0)
  })
})