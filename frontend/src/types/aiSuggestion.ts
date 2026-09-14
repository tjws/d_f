export type AISuggestionStatus =
  | 'draft'
  | 'edited'
  | 'accepted'
  | 'rejected'
  | 'expired'

export interface AISuggestion {
  id: number
  customer_id: number
  user_id: number | null
  profile_id: number | null
  suggestion_type: string
  content: Record<string, unknown>
  edited_content: Record<string, unknown> | null
  evidence: Array<Record<string, unknown>>
  evidence_level: string
  status: AISuggestionStatus
  model_name: string
  model_version: string
  prompt_version: string
  decided_by: number | null
  decided_at: string | null
  created_at: string
}

export interface AISuggestionUpdate {
  content: Record<string, unknown>
}
