import { apiRequest } from './http'
import type { AIDashboard } from '../types/aiDashboard'

export function getAIDashboard(params: { start?: string; end?: string } = {}): Promise<AIDashboard> {
  const query = new URLSearchParams()
  if (params.start) query.set('start', params.start)
  if (params.end) query.set('end', params.end)
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return apiRequest<AIDashboard>(`/admin/ai-dashboard${suffix}`)
}
