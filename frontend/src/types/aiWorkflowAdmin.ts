export type WorkflowRunStatus = 'queued' | 'running' | 'paused' | 'waiting_human' | 'succeeded' | 'failed'

export interface AIWorkflowRunAdmin {
  id: number
  customer_id: number
  actor_user_id: number | null
  goal: string
  provider_name: string
  status: WorkflowRunStatus
  attempt_count: number
  error_code: string | null
  next_action: string | null
  suggestion_count: number
  created_at: string
  started_at: string | null
  heartbeat_at: string | null
  finished_at: string | null
  max_attempts: number
  retryable: boolean
}

export interface AIWorkflowRunAdminList {
  items: AIWorkflowRunAdmin[]
  total: number
}

export interface AIWorkflowRecoveryRead {
  marked_failed: number
  run_ids: number[]
  stale_after_seconds: number
}
