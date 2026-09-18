import { apiRequest } from './http'

export interface AdminUser {
  id: number
  username: string
  full_name: string | null
  role: string
  organization_id: number | null
  is_active: boolean
}

export function listUsers(): Promise<AdminUser[]> {
  return apiRequest<AdminUser[]>('/users')
}
