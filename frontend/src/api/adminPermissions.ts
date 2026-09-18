import { apiRequest } from './http'

export type PermissionRole = 'admin' | 'manager' | 'sales'
export type PermissionScope = 'own' | 'team' | 'organization' | 'all'

export interface AdminPermission {
  id: number
  role: PermissionRole
  module: string
  action: string
  data_scope: PermissionScope
  created_at: string
  updated_at: string
}

export function getAdminPermissions(params: { role?: PermissionRole; module?: string } = {}): Promise<AdminPermission[]> {
  const query = new URLSearchParams()
  if (params.role) query.set('role', params.role)
  if (params.module) query.set('module', params.module)
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return apiRequest<AdminPermission[]>(`/admin/permissions${suffix}`)
}

export function updateAdminPermission(permissionId: number, data_scope: PermissionScope): Promise<AdminPermission> {
  return apiRequest<AdminPermission>(`/admin/permissions/${permissionId}`, {
    method: 'PATCH',
    body: JSON.stringify({ data_scope }),
  })
}
