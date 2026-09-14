export type AIWorkflowRun = {
  customer_id: number
  status: 'waiting_human' | 'failed'
  suggestion_ids: number[]
  error: string | null
}
