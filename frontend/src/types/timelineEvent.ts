export interface TimelineEvent {
  id: number
  customer_id: number
  operator_id: number | null
  occurred_at: string
  event_type: string
  summary: string
  source: string
  reference_type: string | null
  reference_id: string | null
  created_at: string
}

export interface TimelineEventCreate {
  event_type: string
  summary: string
  occurred_at?: string | null
  reference_type?: string | null
  reference_id?: string | null
}
