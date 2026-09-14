import { apiRequest } from './http'
import type { AIWorkflowRun } from '../types/aiWorkflow'

export function runAIWorkflow(customerId: number): Promise<AIWorkflowRun> {
  return apiRequest<AIWorkflowRun>(
    `/customers/${customerId}/ai-workflow`,
    { method: 'POST' },
  )
}
