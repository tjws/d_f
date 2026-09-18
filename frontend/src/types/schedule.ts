import type { AIEvidence } from './ai'

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
  outcome: string | null
  completion_note: string | null
  completed_at: string | null
  evidence: AIEvidence[]
  confirmed_by: number | null
  confirmed_at: string | null
  wecom_calendar_id: string | null
  created_at: string
  updated_at: string
}

export type ScheduleOutcome = 'contacted' | 'no_response' | 'appointment' | 'converted' | 'lost' | 'other'

export interface ScheduleCompletion {
  outcome: ScheduleOutcome
  completion_note?: string | null
}

export interface ScheduleUpdate {
  title?: string
  description?: string | null
  due_at?: string
  priority?: 'low' | 'normal' | 'high'
}
