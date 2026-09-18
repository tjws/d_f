import { apiRequest } from './http'

export type AIRolloutMode = 'all' | 'pilot'
export type AIRolloutSegment = 'new' | 'experienced' | 'unclassified'

export interface AIRolloutConfig {
  mode: AIRolloutMode
  active_member_count: number
  max_member_count: number
}

export interface AIRolloutMember {
  id: number
  user_id: number
  username: string
  full_name: string | null
  role: string
  segment: AIRolloutSegment
  status: 'active' | 'removed'
  added_by: number | null
  started_at: string
  ended_at: string | null
  created_at: string
}

export interface AIRolloutReport {
  id: number
  report_date: string
  cohort: string
  metrics: Record<string, unknown>
  generated_by: number | null
  created_at: string
  updated_at: string
}

export function getAIRolloutConfig(): Promise<AIRolloutConfig> {
  return apiRequest('/admin/ai-rollout/config')
}

export function updateAIRolloutMode(mode: AIRolloutMode): Promise<AIRolloutConfig> {
  return apiRequest('/admin/ai-rollout/config', { method: 'PUT', body: JSON.stringify({ mode }) })
}

export function listAIRolloutMembers(): Promise<AIRolloutMember[]> {
  return apiRequest('/admin/ai-rollout/members')
}

export function addAIRolloutMember(userId: number, segment: AIRolloutSegment): Promise<AIRolloutMember> {
  return apiRequest('/admin/ai-rollout/members', { method: 'POST', body: JSON.stringify({ user_id: userId, segment }) })
}

export function removeAIRolloutMember(userId: number): Promise<void> {
  return apiRequest(`/admin/ai-rollout/members/${userId}`, { method: 'DELETE' })
}

export function listAIRolloutReports(): Promise<AIRolloutReport[]> {
  return apiRequest('/admin/ai-rollout/reports?limit=30')
}

export function generateAIRolloutReport(reportDate?: string): Promise<AIRolloutReport> {
  const query = reportDate ? `?report_date=${encodeURIComponent(reportDate)}` : ''
  return apiRequest(`/admin/ai-rollout/reports/generate${query}`, { method: 'POST' })
}

