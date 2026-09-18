import { apiRequest } from './http'
import type { AgentControlPayload, AgentExecutionMode, AgentFeedbackAction, AgentTask, SalesAgentResponse } from '../types/agent'

export function runSalesAgent(
  customerId: number,
  payload: { task?: AgentTask; instruction?: string; execution_mode?: AgentExecutionMode; idempotency_key?: string },
): Promise<SalesAgentResponse> {
  return apiRequest<SalesAgentResponse>(
    `/customers/${customerId}/agent/run`,
    { method: 'POST', body: JSON.stringify(payload) },
  )
}

export function controlSalesAgent(
  customerId: number,
  runId: number,
  payload: AgentControlPayload,
): Promise<SalesAgentResponse> {
  return apiRequest<SalesAgentResponse>(
    `/customers/${customerId}/agent/runs/${runId}/control`,
    { method: 'POST', body: JSON.stringify(payload) },
  )
}

export function getSalesAgentRun(customerId: number, runId: number): Promise<SalesAgentResponse> {
  return apiRequest<SalesAgentResponse>(
    `/customers/${customerId}/agent/runs/${runId}`,
  )
}

export function retrySalesAgent(customerId: number, runId: number, confirm = true): Promise<SalesAgentResponse> {
  return apiRequest<SalesAgentResponse>(
    `/customers/${customerId}/agent/runs/${runId}/retry`,
    { method: 'POST', body: JSON.stringify({ confirm }) },
  )
}

export function submitSalesAgentFeedback(customerId: number, runId: number, payload: { action: AgentFeedbackAction; note?: string }): Promise<unknown> {
  return apiRequest<unknown>(`/customers/${customerId}/agent/runs/${runId}/feedback`, {
    method: 'POST', body: JSON.stringify(payload),
  })
}
