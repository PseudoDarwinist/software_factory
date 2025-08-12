/**
 * ADI (Adaptive Domain Intelligence) Type Definitions
 * 
 * Types for the Field Review interface and related components
 */

export interface DecisionCase {
  id: string
  timestamp: string
  domain: string
  decision: string
  reasoning: string
  confidence: number
  isCorrect?: boolean
  failureModes?: FailureMode[]
  rawData: DecisionLogEntry
  similarCases?: string[]
  workItems?: string[]
}

export interface DecisionLogEntry {
  id: string
  timestamp: string
  request: any
  response: any
  context: any
  metadata: {
    model: string
    version: string
    latency: number
    tokens: number
  }
}

export interface FailureMode {
  id: string
  name: string
  category: string
  description: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  frequency?: number
}

export interface DomainKnowledge {
  id?: string
  domain: string
  type: 'policy' | 'rule' | 'example' | 'context'
  content: string
  format: 'yaml' | 'text' | 'json'
  tags?: string[]
  author?: string
  timestamp?: string
}

export interface PolicyRule {
  id: string
  name: string
  domain: string
  condition: string
  action: string
  priority: number
  active: boolean
}

export interface SimilarCase {
  id: string
  similarity: number
  decision: string
  outcome: 'correct' | 'incorrect' | 'unknown'
  timestamp: string
}

export interface EvalSet {
  id: string
  name: string
  domain: string
  description: string
  testCases: number
  lastRun?: string
  status: 'ready' | 'running' | 'completed' | 'failed'
}

export interface EvalResult {
  id: string
  evalSetId: string
  timestamp: string
  accuracy: number
  precision: number
  recall: number
  f1Score: number
  details: {
    passed: number
    failed: number
    total: number
    failures: Array<{
      testCase: string
      expected: string
      actual: string
      reason: string
    }>
  }
}

export interface WorkIdea {
  id: string
  title: string
  description: string
  priority: 'low' | 'medium' | 'high'
  status: 'draft' | 'ready' | 'in_progress' | 'completed'
  sourceCase?: string
  insights: string[]
  createdAt: string
}

export interface DomainMetrics {
  totalCases: number
  correctnessRate: number
  commonFailureModes: Array<{
    mode: string
    frequency: number
    trend: 'increasing' | 'decreasing' | 'stable'
  }>
  confidenceDistribution: Array<{
    range: string
    count: number
  }>
}

export interface DomainPack {
  id: string
  project_id: string
  name: string
  version: string
  owner_team: string
  description?: string
  extends?: string
  status: 'active' | 'draft' | 'deprecated'
  created_at: string
  updated_at: string
  pack_data: {
    defaults?: any
    ontology?: FailureMode[]
    metrics?: MetricConfig[]
    rules?: PolicyRule[]
    knowledge?: DomainKnowledge[]
  }
}

export interface MetricConfig {
  key: string
  label: string
  description: string
  type: 'north_star' | 'supporting'
  compute: string
  target?: number
  unit?: string
}