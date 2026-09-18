import { apiRequest } from './http'

export type AdminTagStatus = 'active' | 'inactive'

export interface AdminTag {
  id: number
  key: string
  name: string
  category: string
  description: string | null
  color: string | null
  status: string
  assignment_count: number
  customer_count: number
  suggested_count: number
  confirmed_count: number
  rejected_count: number
  created_at: string
  updated_at: string
}

export interface AdminTagPayload {
  key: string
  name: string
  category: string
  description?: string | null
  color?: string | null
  status?: AdminTagStatus
}

export function listAdminTags(): Promise<AdminTag[]> {
  return apiRequest<AdminTag[]>('/admin/tags')
}

export function createAdminTag(payload: AdminTagPayload): Promise<AdminTag> {
  return apiRequest<AdminTag>('/admin/tags', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateAdminTag(tagId: number, payload: Partial<AdminTagPayload>): Promise<AdminTag> {
  return apiRequest<AdminTag>(`/admin/tags/${tagId}`, { method: 'PATCH', body: JSON.stringify(payload) })
}
