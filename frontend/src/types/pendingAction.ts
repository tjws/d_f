export type PendingActionType = 'profile' | 'reply' | 'tag' | 'schedule'

export interface PendingAction {
  id: string
  resource_id: number
  action_type: PendingActionType
  customer_id: number
  customer_name: string
  customer_stage: string
  status: string
  title: string
  summary: string
  created_at: string
}

export interface PendingActionListResponse {
  items: PendingAction[]
  total: number
}
