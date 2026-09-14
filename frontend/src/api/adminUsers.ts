import { apiRequest } from './http'
import type { AdminUser, UserRole } from '../types/adminUser'

export function listAdminUsers(): Promise<AdminUser[]> {
  return apiRequest<AdminUser[]>('/users')
}

export function updateUserRole(
  userId: number,
  role: UserRole,
): Promise<AdminUser> {
  return apiRequest<AdminUser>(`/users/${userId}/role`, {
    method: 'PATCH',
    body: JSON.stringify({ role }),
  })
}

export function updateUserOrganization(
  userId: number,
  organizationId: number | null,
): Promise<AdminUser> {
  return apiRequest<AdminUser>(`/users/${userId}/organization`, {
    method: 'PATCH',
    body: JSON.stringify({ organization_id: organizationId }),
  })
}
