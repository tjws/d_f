export interface Schedule {
  id: number
  customer_id: number
  user_id: number | null
  suggestion_id: number | null
  title: string
  description: string | null
  due_at: string
  priority: string
  source: string
  status: string
  evidence: Array<Record<string, unknown>>
  confirmed_by: number | null
  confirmed_at: string | null
  wecom_calendar_id: string | null
  created_at: string
  updated_at: string
}

export interface ScheduleUpdate {
  title?: string
  description?: string | null
  due_at?: string
  priority?: 'low' | 'normal' | 'high'
}
