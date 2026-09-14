export type CustomerProfileStatus =
  | 'draft'
  | 'confirmed'
  | 'rejected'
  | 'archived'

export interface CustomerProfile {
  id: number
  customer_id: number
  version: number
  status: CustomerProfileStatus
  dimensions: Record<string, unknown>
  evidence: Array<Record<string, unknown>>
  model_name: string
  model_version: string
  prompt_version: string
  confirmed_by: number | null
  confirmed_at: string | null
  created_at: string
}

export interface CustomerProfileUpdate {
  dimensions: Record<string, unknown>
}
