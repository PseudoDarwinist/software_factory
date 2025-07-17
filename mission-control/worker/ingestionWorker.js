// ingestionWorker.js - background agent to index repositories and docs
// Node script launched via `npm run worker`
// -----------------------------------------------------------------------------
// Why this exists:
// 1. Off-load long-running Goose + Claude Code indexing from the REST request
// 2. Keep UI responsive – backend fires an event then returns immediately
// 3. Emit progress updates (`project.indexed`, `docs.indexed`) back to the
//    Socket.IO hub so Mission Control can flip its status dots.
// -----------------------------------------------------------------------------

const { io } = require('socket.io-client')
const { spawn } = require('child_process')
const fs = require('fs')
const os = require('os')
const path = require('path')
const crypto = require('crypto')
const dataStore = require('../server/dataStore')

// URL of the Socket.IO hub (same host as Express backend)
const SOCKET_URL = process.env.SOCKET_URL || 'http://localhost:5001'

// Directory where we'll stash system maps & doc chunks (persist between runs)
const ARTIFACTS_DIR = path.join(__dirname, '..', 'artifacts')
if (!fs.existsSync(ARTIFACTS_DIR)) {
  fs.mkdirSync(ARTIFACTS_DIR)
}

console.log('🦆 Ingestion worker starting…')
console.log('Connecting to', SOCKET_URL)

const socket = io(SOCKET_URL, {
  transports: ['websocket'],
})

socket.on('connect', () => {
  console.log('✅ Worker connected to Socket.IO hub as', socket.id)
})

socket.on('disconnect', () => {
  console.warn('⚠️  Worker disconnected – will retry automatically.')
})

//---------------------------------- Helpers ----------------------------------//
function tmpDir () {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'mc-index-'))
}

function run(cmd, args, options = {}) {
  return new Promise((resolve) => {
    const child = spawn(cmd, args, { stdio: 'inherit', ...options })
    child.on('close', (code) => resolve(code))
  })
}

function randomId() {
  return crypto.randomBytes(6).toString('hex')
}

function saveSystemMap(projectId, mapPath) {
  // Persist a copy under artifacts/projectId/system-map.json
  const destDir = path.join(ARTIFACTS_DIR, projectId)
  if (!fs.existsSync(destDir)) fs.mkdirSync(destDir, { recursive: true })
  const dest = path.join(destDir, 'system-map.json')
  fs.copyFileSync(mapPath, dest)
  return dest
}

//---------------------------------- Index Repo ----------------------------------//
async function handleProjectCreated(evt) {
  const { projectId, repoUrl, name } = evt
  console.log(`📥  Indexing repo for ${name} (${projectId}) -> ${repoUrl}`)

  // 1. Clone repo
  const workDir = tmpDir()
  console.log('→ cloning into', workDir)
  const gitCode = await run('git', ['clone', '--depth', '1', repoUrl, workDir])
  if (gitCode !== 0) {
    console.error('❌ git clone failed')
    socket.emit('project.indexed', { projectId, status: 'error', error: 'git clone failed' })
    return
  }

  // 2. Generate system map manually for now (Goose requires interactive session)
  console.log('→ generating system map (manual approach)')
  
  // For now, create a basic system map structure
  // TODO: Implement actual Goose integration when non-interactive mode is available
  const systemMap = {
    timestamp: new Date().toISOString(),
    repository: repoUrl,
    status: 'basic_scan',
    note: 'Manual system map generation - Goose integration pending',
    structure: {
      directories: [],
      files: [],
      languages: [],
      frameworks: []
    }
  }

  // Basic file system scan
  try {
    const files = fs.readdirSync(workDir, { withFileTypes: true })
    systemMap.structure.directories = files.filter(f => f.isDirectory()).map(f => f.name)
    systemMap.structure.files = files.filter(f => f.isFile()).map(f => f.name)
    
    // Simple language detection
    const extensions = systemMap.structure.files.map(f => path.extname(f)).filter(ext => ext)
    systemMap.structure.languages = [...new Set(extensions)]
  } catch (err) {
    console.warn('⚠️  Basic file scan failed:', err.message)
  }

  const mapFile = path.join(workDir, 'system-map.json')
  fs.writeFileSync(mapFile, JSON.stringify(systemMap, null, 2))

  if (!fs.existsSync(mapFile)) {
    console.error('❌ System map generation failed')
    socket.emit('project.indexed', { projectId, status: 'error', error: 'system map generation failed' })
    return
  }

  // 3. Persist map & update datastore
  const persistedPath = saveSystemMap(projectId, mapFile)
  const project = dataStore.projects.find(p => p.id === projectId)
  if (project) {
    project.metadata.systemMapGenerated = true
    project.metadata.systemMapPath = persistedPath
    console.log('💾 Saving project metadata updates to data store...')
    // Force save the changes to data.json
    const fs = require('fs')
    const path = require('path')
    const DATA_PATH = path.join(__dirname, '..', 'server', 'data.json')
    fs.writeFileSync(DATA_PATH, JSON.stringify({ 
      projects: dataStore.projects,
      feedItems: dataStore.feedItems || [],
      conversations: dataStore.conversations || {},
      stages: dataStore.stages || {},
      productBriefs: dataStore.productBriefs || {},
      stageTransitions: dataStore.stageTransitions || []
    }, null, 2))
    console.log('✅ Project metadata saved successfully')
  }

  console.log('✅ System map generated at', persistedPath)
  console.log('🔔 EMITTING project.indexed event with data:', { projectId, status: 'ok' })
  socket.emit('project.indexed', { projectId, status: 'ok' })
  console.log('📡 project.indexed event emitted successfully')
}

//---------------------------------- Index Docs ----------------------------------//
async function handleDocsUploaded(evt) {
  const { projectId, docCount } = evt
  console.log(`📥  Doc upload detected for ${projectId} (${docCount} files)`)
  // Placeholder – real implementation would run goose doc-index
  socket.emit('project.docs.indexed', { projectId, status: 'ok' })
}

//---------------------------------- Wire events --------------------------------//
socket.on('project.created', handleProjectCreated)
socket.on('project.docs.uploaded', handleDocsUploaded)

// Keep process alive
process.stdin.resume()