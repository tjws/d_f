export type MyWorkBucket = 'review' | 'overdue' | 'today' | 'upcoming' | 'historical'
export type MyWorkItemType = 'ai_review' | 'schedule'
export type MyWorkActionType = 'profile' | 'reply' | 'tag' | 'schedule'

export interface MyWorkItem {
  id: string
  resource_id: number
  item_type: MyWorkItemType
  bucket: MyWorkBucket
  action_type: MyWorkActionType | null
  status: string | null
  customer_id: number
  customer_name: string
  customer_stage: string
  title: string
  summary: string
  priority: string | null
  due_at: string | null
  created_at: string
}

export interface MyWorkResponse {
  summary: Record<MyWorkBucket, number>
  items: MyWorkItem[]
}
