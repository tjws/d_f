import { apiRequest } from './http'
import type { AuditLogListResponse } from '../types/auditLog'

export interface AuditLogQuery {
  page?: number
  page_size?: number
  action?: string
  actor_user_id?: number
  target_type?: string
  target_id?: string
}

export function listAuditLogs(
  params: AuditLogQuery = {},
): Promise<AuditLogListResponse> {
  const query = new URLSearchParams()
  query.set('page', String(params.page ?? 1))
  query.set('page_size', String(params.page_size ?? 20))

  if (params.action?.trim()) query.set('action', params.action.trim())
  if (params.actor_user_id) query.set('actor_user_id', String(params.actor_user_id))
  if (params.target_type?.trim()) query.set('target_type', params.target_type.trim())
  if (params.target_id?.trim()) query.set('target_id', params.target_id.trim())

  return apiRequest<AuditLogListResponse>(`/audit-logs?${query.toString()}`)
}
