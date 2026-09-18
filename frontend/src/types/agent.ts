import type { AIWorkflowRun } from './aiWorkflow'

export type AgentIntent = 'reply' | 'tag' | 'schedule' | 'comprehensive'
export type AgentTask = 'auto' | AgentIntent

export interface AgentToolTrace {
  name: string
  status: 'ok' | 'skipped' | 'incomplete' | 'error'
  detail: string
}

export interface AgentStep {
  step: number
  tool_name: string
  status: 'ok' | 'skipped' | 'incomplete' | 'error'
  summary: string
  data: Record<string, unknown>
  evidence: Array<Record<string, unknown>>
  missing_inputs: string[]
}

export interface SalesAgentResponse {
  agent_name: string
  intent: AgentIntent
  selected_tool: string
  planned_by: 'bailian' | 'mock' | 'explicit_task'
  planner_run_id: number | null
  human_confirmation_required: boolean
  tool_trace: AgentToolTrace[]
  steps: AgentStep[]
  workflow: AIWorkflowRun
  metadata: Record<string, unknown>
}

export type AgentExecutionMode = 'complete' | 'checkpointed'
export type AgentControlAction = 'pause' | 'correct' | 'resume'
export type AgentFeedbackAction = 'incorrect_reasoning' | 'missing_information' | 'not_useful'

export interface AgentControlPayload {
  action: AgentControlAction
  correction?: { skip_tools: string[]; note?: string }
  step_limit?: number
}
