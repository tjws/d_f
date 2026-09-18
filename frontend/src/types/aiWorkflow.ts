export type AIWorkflowGoal = 'profile' | 'reply' | 'tag' | 'schedule'

export type AIWorkflowRun = {
  run_id: number | null
  customer_id: number
  status: 'queued' | 'running' | 'paused' | 'waiting_human' | 'failed'
  suggestion_ids: number[]
  customer_tag_ids: number[]
  profile_id: number | null
  next_action: 'confirm_profile' | 'review_reply' | 'confirm_tags' | 'review_schedule' | 'resume_agent' | null
  error: string | null
  attempt_count: number
  max_attempts: number
  retryable: boolean
}
