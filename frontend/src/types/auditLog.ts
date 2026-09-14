export interface AuditLog {
  id: number
  actor_user_id: number | null
  actor_username_snapshot: string | null
  actor_role_snapshot: string | null
  actor_source: string
  action: string
  target_type: string
  target_id: string
  detail_json: Record<string, unknown> | null
  result: string
  ip_address: string | null
  request_id: string | null
  created_at: string
}

export interface AuditLogListResponse {
  items: AuditLog[]
  total: number
  page: number
  page_size: number
}
