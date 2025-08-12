import type { ValidationCheck, ValidationCheckStatus, ValidationCheckType, ValidationEvidence, LogEntry, TestResult, PerformanceMetric, Screenshot } from '@/types/validation'

type Subscriber = (checks: ValidationCheck[]) => void

interface ScenarioConfig {
  errorRate: number // 0..1
  warningRate: number // 0..1
  runningCount: number // desired number of running checks
  addRemoveProbability: number // chance to add/remove a check on tick
}

const DEFAULT_SCENARIO: ScenarioConfig = {
  errorRate: 0.1,
  warningRate: 0.2,
  runningCount: 1,
  addRemoveProbability: 0.15,
}

let currentChecks: ValidationCheck[] = []
let subscribers: Set<Subscriber> = new Set()
let timer: any = null
let scenario: ScenarioConfig = { ...DEFAULT_SCENARIO }

const CHECK_NAMES: Record<ValidationCheckType, string[]> = {
  test: [
    'All integration suite',
    'Smoke tests',
    'Regression pack',
    'E2E journey validation',
  ],
  deployment: [
    'Gate-Change Template eval',
    'Canary health checks',
  ],
  monitoring: [
    'Delay email SLA check',
    'Error rate spike detection',
  ],
  security: [
    'SAST scan',
    'Dependency vulnerabilities',
  ],
  performance: [
    'Performance budgets',
    'Lighthouse metrics',
  ],
}

function randomChoice<T>(arr: T[]): T { return arr[Math.floor(Math.random() * arr.length)] }

function randomType(): ValidationCheckType {
  return randomChoice(['test','deployment','monitoring','security','performance']) as ValidationCheckType
}

function randomStatus(): ValidationCheckStatus {
  return randomChoice(['pending','running','success','warning','error']) as ValidationCheckStatus
}

function generateId(): string { return Math.random().toString(36).slice(2, 10) }

function generateCheck(type?: ValidationCheckType): ValidationCheck {
  const t = type || randomType()
  const name = randomChoice(CHECK_NAMES[t])
  const base: ValidationCheck = {
    id: generateId(),
    name,
    type: t,
    status: 'pending',
    timestamp: new Date(),
    duration: Math.floor(Math.random() * 180_000), // up to 3 min
    progress: Math.floor(Math.random() * 100),
    metadata: {},
    priority: randomChoice(['low','medium','high']),
  }
  // enrich metadata
  if (t === 'test') base.metadata.passRate = `${Math.floor(Math.random() * 20) + 25}/${Math.floor(Math.random() * 10) + 30}`
  if (t === 'monitoring') base.metadata.sla = randomChoice(['ok','late'])
  if (t === 'deployment') base.metadata.accuracy = `${Math.floor(Math.random()*10)+90}%`
  return base
}

export function generateEvidenceFor(check: ValidationCheck): ValidationEvidence {
  const logs: LogEntry[] = Array.from({ length: 6 }, (_, i) => ({
    timestamp: new Date(Date.now() - i * 2000),
    level: randomChoice(['info','warn','error']),
    message: `${check.name}: log line ${i+1}`
  }))
  const testResults: TestResult[] | undefined = check.type === 'test' ? Array.from({ length: 5 }, (_, i) => ({
    name: `${check.name} #${i+1}`,
    status: randomChoice(['pass','pass','fail','skip']),
    durationMs: Math.floor(Math.random()*2000),
    errorMessage: Math.random() < 0.2 ? 'AssertionError: expected true to be false' : undefined,
  })) : undefined
  const performanceMetrics: PerformanceMetric[] | undefined = check.type === 'performance' ? [
    { name: 'TTFB', value: Math.random()*200 + 100, unit: 'ms', target: 200 },
    { name: 'LCP', value: Math.random()*1000 + 1500, unit: 'ms', target: 2500 },
  ] : undefined
  const screenshots: Screenshot[] | undefined = check.type === 'deployment' ? [
    { id: generateId(), url: 'about:blank', caption: 'Deployment Dashboard' }
  ] : undefined
  return { logs, testResults, performanceMetrics, screenshots }
}

function ensureInitialData() {
  if (currentChecks.length) return
  // Create a stable set mixing statuses
  currentChecks = [
    { ...generateCheck('test'), status: 'success', progress: 100, duration: 120_000 },
    { ...generateCheck('test'), status: 'success', progress: 100, duration: 90_000 },
    { ...generateCheck('monitoring'), status: 'warning', progress: 100, duration: 30_000 },
    { ...generateCheck('deployment'), status: 'success', progress: 100, duration: 45_000 },
    { ...generateCheck('performance'), status: 'running', progress: 75 },
  ]
}

function emit() {
  for (const cb of subscribers) cb([...currentChecks])
}

function tick() {
  // Randomly update timestamps and statuses
  const now = Date.now()
  for (const c of currentChecks) {
    // advance time
    c.timestamp = new Date(now - Math.floor(Math.random()*180_000))

    // adjust running and progress
    if (c.status === 'running') {
      c.progress = Math.min(100, (c.progress || 0) + Math.floor(Math.random()*20))
      if ((c.progress || 0) >= 100) {
        c.status = Math.random() < scenario.errorRate ? 'error' : (Math.random() < scenario.warningRate ? 'warning' : 'success')
        c.duration = (c.duration || 0) + Math.floor(Math.random()*30_000)
      }
    } else if (Math.random() < 0.1) {
      // occasionally flip between pending and running
      if (c.status === 'pending') {
        c.status = 'running'
        c.progress = Math.floor(Math.random()*30)
      }
    }
  }

  // Target a desired number of running checks
  const running = currentChecks.filter(c => c.status === 'running').length
  if (running < scenario.runningCount && currentChecks.length) {
    const candidates = currentChecks.filter(c => c.status === 'pending' || c.status === 'warning')
    if (candidates.length) randomChoice(candidates).status = 'running'
  }

  // Add/remove checks sometimes
  if (Math.random() < scenario.addRemoveProbability) {
    if (Math.random() < 0.5 && currentChecks.length > 3) {
      currentChecks.splice(Math.floor(Math.random()*currentChecks.length), 1)
    } else {
      currentChecks.push(generateCheck())
    }
  }

  emit()
}

export const MockValidationService = {
  start(projectId?: string, intervalMs = 4000) {
    ensureInitialData()
    if (!timer) timer = setInterval(tick, intervalMs)
    emit()
  },
  stop() {
    if (timer) clearInterval(timer)
    timer = null
  },
  refresh() {
    // Force immediate update
    tick()
  },
  getChecks(): ValidationCheck[] {
    ensureInitialData()
    return [...currentChecks]
  },
  subscribe(cb: Subscriber): () => void {
    subscribers.add(cb)
    cb([...currentChecks])
    return () => {
      subscribers.delete(cb)
    }
  },
  setScenario(next: Partial<ScenarioConfig>) {
    scenario = { ...scenario, ...next }
  }
}

export default MockValidationService

