/**
 * ADI API Service
 * 
 * Handles communication with the ADI backend services
 */

import type { 
  DecisionCase, 
  FailureMode, 
  DomainKnowledge, 
  EvalSet, 
  EvalResult,
  WorkIdea,
  DomainMetrics,
  PolicyRule,
  SimilarCase,
  DomainPack,
  MetricConfig
} from '@/types/adi'

const API_BASE = '/api/adi'

class ADIApiService {
  // Decision Cases
  async getDecisionCases(domain?: string, limit = 50): Promise<DecisionCase[]> {
    const params = new URLSearchParams()
    if (domain) params.append('domain', domain)
    params.append('limit', limit.toString())
    
    const response = await fetch(`${API_BASE}/cases?${params}`)
    if (!response.ok) throw new Error('Failed to fetch decision cases')
    return response.json()
  }

  async getDecisionCase(id: string): Promise<DecisionCase> {
    const response = await fetch(`${API_BASE}/cases/${id}`)
    if (!response.ok) throw new Error('Failed to fetch decision case')
    return response.json()
  }

  async updateCaseCorrectness(caseId: string, isCorrect: boolean): Promise<void> {
    const response = await fetch(`${API_BASE}/cases/${caseId}/correctness`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ isCorrect })
    })
    if (!response.ok) throw new Error('Failed to update case correctness')
  }

  // Failure Mode Tagging
  async getFailureModes(domain?: string): Promise<FailureMode[]> {
    const params = domain ? `?domain=${domain}` : ''
    const response = await fetch(`${API_BASE}/failure-modes${params}`)
    if (!response.ok) throw new Error('Failed to fetch failure modes')
    return response.json()
  }

  async tagFailureMode(caseId: string, failureMode: FailureMode): Promise<void> {
    const response = await fetch(`${API_BASE}/cases/${caseId}/failure-modes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ failureMode })
    })
    if (!response.ok) throw new Error('Failed to tag failure mode')
  }

  // Domain Knowledge
  async addDomainKnowledge(knowledge: DomainKnowledge): Promise<DomainKnowledge> {
    const response = await fetch(`${API_BASE}/knowledge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(knowledge)
    })
    if (!response.ok) throw new Error('Failed to add domain knowledge')
    return response.json()
  }

  async getDomainKnowledge(domain: string): Promise<DomainKnowledge[]> {
    const response = await fetch(`${API_BASE}/knowledge?domain=${domain}`)
    if (!response.ok) throw new Error('Failed to fetch domain knowledge')
    return response.json()
  }

  async rescoreSimilarCases(domain: string): Promise<void> {
    const response = await fetch(`${API_BASE}/rescore`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ domain })
    })
    if (!response.ok) throw new Error('Failed to rescore similar cases')
  }

  // Policy Rules
  async getPolicyRules(domain: string): Promise<PolicyRule[]> {
    const response = await fetch(`${API_BASE}/policies?domain=${domain}`)
    if (!response.ok) throw new Error('Failed to fetch policy rules')
    return response.json()
  }

  // Similar Cases
  async getSimilarCases(caseId: string): Promise<SimilarCase[]> {
    const response = await fetch(`${API_BASE}/cases/${caseId}/similar`)
    if (!response.ok) throw new Error('Failed to fetch similar cases')
    return response.json()
  }

  // Evaluation Sets
  async getEvalSets(domain?: string): Promise<EvalSet[]> {
    const params = domain ? `?domain=${domain}` : ''
    const response = await fetch(`${API_BASE}/eval-sets${params}`)
    if (!response.ok) throw new Error('Failed to fetch eval sets')
    return response.json()
  }

  async executeEvalSet(evalSetId: string): Promise<string> {
    const response = await fetch(`${API_BASE}/eval-sets/${evalSetId}/execute`, {
      method: 'POST'
    })
    if (!response.ok) throw new Error('Failed to execute eval set')
    const result = await response.json()
    return result.executionId
  }

  async getEvalResults(evalSetId: string): Promise<EvalResult[]> {
    const response = await fetch(`${API_BASE}/eval-sets/${evalSetId}/results`)
    if (!response.ok) throw new Error('Failed to fetch eval results')
    return response.json()
  }

  async getEvalExecution(executionId: string): Promise<EvalResult> {
    const response = await fetch(`${API_BASE}/eval-executions/${executionId}`)
    if (!response.ok) throw new Error('Failed to fetch eval execution')
    return response.json()
  }

  // Work Ideas (Think stage integration)
  async createWorkIdea(insight: string, context: any): Promise<WorkIdea> {
    const response = await fetch(`${API_BASE}/work-ideas`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ insight, context })
    })
    if (!response.ok) throw new Error('Failed to create work idea')
    return response.json()
  }

  async getWorkIdeas(sourceCase?: string): Promise<WorkIdea[]> {
    const params = sourceCase ? `?sourceCase=${sourceCase}` : ''
    const response = await fetch(`${API_BASE}/work-ideas${params}`)
    if (!response.ok) throw new Error('Failed to fetch work ideas')
    return response.json()
  }

  // Metrics and Analytics
  async getDomainMetrics(domain: string): Promise<DomainMetrics> {
    const response = await fetch(`${API_BASE}/metrics?domain=${domain}`)
    if (!response.ok) throw new Error('Failed to fetch domain metrics')
    return response.json()
  }

  // Domain Pack Management
  async getDomainPack(projectId: string): Promise<DomainPack> {
    const response = await fetch(`${API_BASE}/packs/${projectId}`)
    if (!response.ok) throw new Error('Failed to fetch domain pack')
    return response.json()
  }

  async updateDomainPack(projectId: string, updates: Partial<DomainPack>): Promise<DomainPack> {
    const response = await fetch(`${API_BASE}/packs/${projectId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates)
    })
    if (!response.ok) throw new Error('Failed to update domain pack')
    return response.json()
  }

  async deployDomainPack(projectId: string, version?: string): Promise<void> {
    const response = await fetch(`${API_BASE}/packs/${projectId}/deploy`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ version })
    })
    if (!response.ok) throw new Error('Failed to deploy domain pack')
  }

  async getPackVersions(projectId: string): Promise<Array<{ version: string; deployed_at: string; status: string }>> {
    const response = await fetch(`${API_BASE}/packs/${projectId}/versions`)
    if (!response.ok) throw new Error('Failed to fetch pack versions')
    return response.json()
  }

  async rollbackDomainPack(projectId: string, version: string): Promise<void> {
    const response = await fetch(`${API_BASE}/packs/${projectId}/rollback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ version })
    })
    if (!response.ok) throw new Error('Failed to rollback domain pack')
  }
}

export const adiApi = new ADIApiService()