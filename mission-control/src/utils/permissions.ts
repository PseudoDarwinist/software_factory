export interface ValidationPermissions {
  canViewValidation: boolean
  canApproveValidation: boolean
  canOverrideValidation: boolean
  canRetryValidation: boolean
  canAccessLogs: boolean
  canAccessEvidence: boolean
  canRejectValidation: boolean
  canCreateBug: boolean
}

export function getValidationPermissions(): ValidationPermissions {
  const hasToken = !!localStorage.getItem('auth_token')
  let roles: string[] = []
  try {
    const raw = localStorage.getItem('auth_roles')
    roles = raw ? JSON.parse(raw) : []
  } catch {
    roles = []
  }

  const isAdmin = roles.includes('admin') || roles.includes('qa_lead')
  const isApprover = roles.includes('approver') || roles.includes('product_owner')
  const isEngineer = roles.includes('devops') || roles.includes('engineer')
  const isQA = roles.includes('qa') || roles.includes('qa_lead')

  return {
    canViewValidation: true,
    canApproveValidation: hasToken && (isAdmin || isApprover),
    canOverrideValidation: hasToken && isAdmin,
    canRetryValidation: hasToken && (isAdmin || isEngineer),
    canAccessLogs: true,
    canAccessEvidence: true,
    canRejectValidation: hasToken && (isAdmin || isApprover),
    canCreateBug: hasToken && (isAdmin || isEngineer || isQA),
  }
}

export function getCurrentUser(): string | null {
  const u = localStorage.getItem('auth_user')
  if (!u) return null
  try {
    const parsed = JSON.parse(u)
    return parsed?.email || parsed?.name || null
  } catch {
    return u
  }
}

