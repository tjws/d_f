import { apiRequest } from './http'
import type { SystemStatus } from '../types/systemStatus'

export function getSystemStatus(): Promise<SystemStatus> {
  return apiRequest<SystemStatus>('/admin/system-status')
}
