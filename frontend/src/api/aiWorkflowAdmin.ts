import { apiRequest } from './http'
import type {
  AIWorkflowRecoveryRead,
  AIWorkflowRunAdminList,
  WorkflowRunStatus,
} from '../types/aiWorkflowAdmin'

export function listAIWorkflowRuns(params: {
  start?: string
  end?: string
  provider_name?: string
  status?: WorkflowRunStatus
  limit?: number
} = {}): Promise<AIWorkflowRunAdminList> {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') query.set(key, String(value))
  }
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return apiRequest<AIWorkflowRunAdminList>(`/admin/ai-workflow-runs${suffix}`)
}

export function recoverStaleWorkflowRuns(payload: {
  confirm: boolean
  stale_after_seconds?: number
  limit?: number
} = { confirm: true }): Promise<AIWorkflowRecoveryRead> {
  return apiRequest<AIWorkflowRecoveryRead>('/admin/ai-workflow-runs/recover-stale', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
