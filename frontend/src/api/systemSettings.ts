import { apiRequest } from './http'
import type { SystemSetting } from '../types/systemSetting'

export function listSystemSettings(): Promise<SystemSetting[]> {
  return apiRequest<SystemSetting[]>('/admin/system-settings')
}

export function updateSystemSetting(key: string, value: number | boolean): Promise<SystemSetting> {
  return apiRequest<SystemSetting>(`/admin/system-settings/${key}`, { method: 'PUT', body: JSON.stringify({ value }) })
}
