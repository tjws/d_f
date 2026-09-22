import { apiRequest } from './http'
import type {
  ChurnBatchStatus,
  ChurnRiskBatchDetail,
  ChurnRiskLevel,
  ChurnScoringBatchList,
  ChurnIntervention,
  ChurnInterventionOutcome,
  ChurnInterventionStatus,
  ChurnModelVersion,
  ExternalStudentMapping,
} from '../types/churnRisk'

export function listChurnScoringBatches(params: {
  start?: string
  end?: string
  status?: ChurnBatchStatus
  limit?: number
} = {}): Promise<ChurnScoringBatchList> {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') query.set(key, String(value))
  }
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return apiRequest<ChurnScoringBatchList>(`/admin/churn-risks/batches${suffix}`)
}

export function createExternalStudentMapping(payload: {
  source_system: string
  external_student_id: string
  student_id: number
}): Promise<ExternalStudentMapping> {
  return apiRequest<ExternalStudentMapping>('/admin/churn-risks/mappings', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function createChurnIntervention(predictionId: number, payload: {
  action_type: string
  due_at: string
  note?: string
}): Promise<ChurnIntervention> {
  return apiRequest<ChurnIntervention>(`/admin/churn-risks/predictions/${predictionId}/intervention`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateChurnIntervention(interventionId: number, payload: {
  status: ChurnInterventionStatus
  outcome?: ChurnInterventionOutcome
  note?: string
}): Promise<ChurnIntervention> {
  return apiRequest<ChurnIntervention>(`/admin/churn-risks/interventions/${interventionId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function listChurnModels(): Promise<ChurnModelVersion[]> {
  return apiRequest<ChurnModelVersion[]>('/admin/churn-risks/models')
}

export function registerChurnModel(payload: {
  artifact_filename: string
  report_filename?: string
  version: string
}): Promise<ChurnModelVersion> {
  return apiRequest<ChurnModelVersion>('/admin/churn-risks/models', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function approveChurnModel(modelId: number): Promise<ChurnModelVersion> {
  return apiRequest<ChurnModelVersion>(`/admin/churn-risks/models/${modelId}/approve`, { method: 'POST' })
}

export function getChurnScoringBatch(batchId: number, params: {
  risk_level?: ChurnRiskLevel
  keyword?: string
  page?: number
  page_size?: number
} = {}): Promise<ChurnRiskBatchDetail> {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== '') query.set(key, String(value))
  }
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return apiRequest<ChurnRiskBatchDetail>(`/admin/churn-risks/batches/${batchId}${suffix}`)
}
