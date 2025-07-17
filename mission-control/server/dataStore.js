const fs = require('fs')
const path = require('path')

const DATA_PATH = path.join(__dirname, 'data.json')

// Default seed values fall back to previous mock data so existing UI works
const defaultData = {
  projects: [
    {
      id: 'proj-1',
      name: 'Software Factory',
      health: 'green',
      unreadCount: 0,
      lastActivity: new Date().toISOString(),
      description: 'Main platform development',
    },
    {
      id: 'proj-2',
      name: 'Mission Control',
      health: 'amber',
      unreadCount: 3,
      lastActivity: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
      description: 'Command center interface',
    },
    {
      id: 'proj-3',
      name: 'AI Agents',
      health: 'red',
      unreadCount: 7,
      lastActivity: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
      description: 'Autonomous development agents',
    },
  ],
  // Enterprise channel-to-project mapping
  channelMappings: {
    'C095S2NQQMV': 'proj-1', // Default ideas channel -> Software Factory
    'C095S2NQQMW': 'proj-2', // Mission Control discussions
    'C095S2NQQMX': 'proj-3', // AI Agents development
  },
  // Stage data for SDLC workflow
  stages: {
    'proj-1': {
      think: [],
      define: [],
      plan: [],
      build: [],
      validate: []
    },
    'proj-2': {
      think: [],
      define: [],
      plan: [],
      build: [],
      validate: []
    },
    'proj-3': {
      think: [],
      define: [],
      plan: [],
      build: [],
      validate: []
    }
  },
  // Product briefs for Define stage
  productBriefs: {},
  // Stage transition history
  stageTransitions: [],
  feedItems: [
    {
      id: 'feed-1',
      projectId: 'proj-3',
      severity: 'red',
      kind: 'ci_fail',
      title: 'Payment flow broke on Safari',
      summary: 'Checkout test failing on Safari 17 with currency formatting error',
      createdAt: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
      updatedAt: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
      linkedArtifactIds: ['pr-77', 'test-901'],
      unread: true,
      actor: 'CI System',
      metadata: {
        browser: 'Safari',
        testSuite: 'checkout',
        errorType: 'currency_format',
      },
    },
    {
      id: 'feed-2',
      projectId: 'proj-2',
      severity: 'amber',
      kind: 'spec_change',
      title: 'Spacing updated, review visual diffs?',
      summary: 'Designer Sara updated button spacing in the header component',
      createdAt: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
      updatedAt: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
      linkedArtifactIds: ['figma-123', 'design-456'],
      unread: true,
      actor: 'Sara (Designer)',
      metadata: {
        component: 'header',
        changeType: 'spacing',
        figmaFrame: 'frame-123',
      },
    },
    {
      id: 'feed-3',
      projectId: 'proj-1',
      severity: 'info',
      kind: 'idea',
      title: 'Offer users Dark Mode',
      summary: 'Marketing says lots of users ask for dark mode support',
      createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
      updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(),
      linkedArtifactIds: [],
      unread: true,
      actor: 'Marketing Team',
      metadata: {
        source: 'user_feedback',
        priority: 'medium',
      },
    },
    {
      id: 'feed-4',
      projectId: 'proj-2',
      severity: 'amber',
      kind: 'pr_review',
      title: 'Liquid glass animations ready for review',
      summary: 'New animation system for Mission Control interface',
      createdAt: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
      updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
      linkedArtifactIds: ['pr-89'],
      unread: false,
      actor: 'Alex (Developer)',
      metadata: {
        prNumber: 89,
        changes: 15,
        additions: 234,
        deletions: 12,
      },
    },
  ],
  conversations: {},
}

function loadData() {
  if (fs.existsSync(DATA_PATH)) {
    try {
      const raw = fs.readFileSync(DATA_PATH, 'utf-8')
      return JSON.parse(raw)
    } catch (err) {
      console.warn('Could not parse data.json, falling back to defaults', err)
    }
  }
  return { ...defaultData }
}

let store = loadData()

// ---------------------------------------------------------------------------
// Ensure previously persisted data has all required top-level collections. If
// someone saved an older schema without these keys, accessing them later would
// throw "Cannot read properties of undefined" errors (observed for
// `productBriefs` and `stages`). We defensively add them here so the rest of
// the API can assume they are present.
// ---------------------------------------------------------------------------

if (!store.stages) {
  store.stages = {}
}

if (!store.productBriefs) {
  store.productBriefs = {}
}

if (!store.stageTransitions) {
  store.stageTransitions = []
}

// Persist immediately so the file on disk is upgraded to the latest shape and
// we don’t have to fix it again on the next server restart.
persist()

function persist() {
  fs.writeFileSync(DATA_PATH, JSON.stringify(store, null, 2))
}

// Basic helpers (extend as needed)
module.exports = {
  get projects() {
    return store.projects
  },
  get feedItems() {
    return store.feedItems
  },
  get conversations() {
    return store.conversations
  },
  addFeedItem(item) {
    store.feedItems.unshift(item)
    // Auto-add to Think stage
    if (item.kind === 'idea' && item.projectId) {
      if (!store.stages[item.projectId]) {
        store.stages[item.projectId] = {
          think: [], define: [], plan: [], build: [], validate: []
        }
      }
      store.stages[item.projectId].think.push(item.id)
    }
    persist()
  },
  updateFeedItem(id, fields) {
    const idx = store.feedItems.findIndex((f) => f.id === id)
    if (idx !== -1) {
      store.feedItems[idx] = { ...store.feedItems[idx], ...fields }
      persist()
    }
  },
  markFeedRead(id) {
    const item = store.feedItems.find((f) => f.id === id)
    if (item) {
      item.unread = false
      persist()
    }
  },
  addProject(project) {
    store.projects.push(project)
    // Initialize stages for the new project
    if (!store.stages[project.id]) {
      store.stages[project.id] = {
        think: [], define: [], plan: [], build: [], validate: []
      }
    }
    persist()
  },
  removeProject(projectId) {
    // Remove from projects array
    store.projects = store.projects.filter(p => p.id !== projectId)
    // Remove stages data
    delete store.stages[projectId]
    persist()
  },
  // Channel-to-project mapping helpers
  getProjectForChannel(channelId) {
    return store.channelMappings[channelId] || null
  },
  addChannelMapping(channelId, projectId) {
    store.channelMappings[channelId] = projectId
    persist()
  },
  // Stage management
  moveItemToStage(itemId, fromStage, toStage, projectId) {
    if (!store.stages[projectId]) {
      store.stages[projectId] = {
        think: [], define: [], plan: [], build: [], validate: []
      }
    }
    
    // Remove from current stage
    if (fromStage && store.stages[projectId][fromStage]) {
      const fromIndex = store.stages[projectId][fromStage].indexOf(itemId)
      if (fromIndex > -1) {
        store.stages[projectId][fromStage].splice(fromIndex, 1)
      }
    }
    
    // Add to new stage
    if (toStage && store.stages[projectId][toStage]) {
      store.stages[projectId][toStage].push(itemId)
    }
    
    // Record transition
    store.stageTransitions.push({
      id: Date.now().toString(),
      itemId,
      fromStage,
      toStage,
      projectId,
      timestamp: new Date().toISOString(),
      actor: 'system' // TODO: get actual user
    })
    
    persist()
  },
  // Product Brief management
  createProductBrief(itemId, projectId, briefData) {
    const briefId = `brief-${itemId}`
    store.productBriefs[briefId] = {
      id: briefId,
      itemId,
      projectId,
      ...briefData,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      version: 1,
      status: 'draft'
    }
    persist()
    return store.productBriefs[briefId]
  },
  updateProductBrief(briefId, fields) {
    if (store.productBriefs[briefId]) {
      store.productBriefs[briefId] = {
        ...store.productBriefs[briefId],
        ...fields,
        updatedAt: new Date().toISOString()
      }
      persist()
    }
  },
  getProductBrief(briefId) {
    return store.productBriefs[briefId] || null
  },
  freezeProductBrief(briefId) {
    if (store.productBriefs[briefId]) {
      store.productBriefs[briefId].status = 'frozen'
      store.productBriefs[briefId].frozenAt = new Date().toISOString()
      persist()
    }
  },
  save: persist,
} 