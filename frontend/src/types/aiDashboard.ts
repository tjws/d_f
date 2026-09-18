export interface AIDashboard {
  start: string
  end: string
  suggestions_total: number
  feedback_total: number
  accepted: number
  edited: number
  rejected: number
  adoption_rate: number
  by_suggestion_type: Record<string, { suggestions: number; accepted: number; edited: number; rejected: number }>
  workflow: { succeeded: number; failed: number; waiting_human: number }
  bailian_calls: number
  bailian_failures: number
  rag_queries_total: number
  rag_fallbacks: number
  rag_fallback_rate: number
  agent_feedback_total: number
  agent_feedback_by_action: Record<string, number>
  agent_reasoning_total: number
  agent_reasoning_failures: number
  agent_reasoning_failure_rate: number
  avg_task_duration_ms: number
}
