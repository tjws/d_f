export interface SystemSetting {
  id: number
  key: string
  value: unknown
  scope_type: string
  scope_id: number | null
  description: string | null
  updated_by: number | null
  updated_at: string
}
