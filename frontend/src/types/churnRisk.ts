export type ChurnBatchStatus = 'running' | 'completed' | 'failed'
export type ChurnRiskLevel = 'high' | 'medium' | 'low'
export type ChurnInterventionStatus = 'planned' | 'in_progress' | 'completed' | 'cancelled'
export type ChurnInterventionOutcome = 'retained' | 'recovered' | 'churned' | 'unknown'

export interface ChurnIntervention {
  id: number
  prediction_id: number
  customer_id: number
  student_id: number
  actor_user_id: number | null
  schedule_id: number | null
  action_type: string
  status: ChurnInterventionStatus
  outcome: ChurnInterventionOutcome | null
  note: string | null
  due_at: string
  completed_at: string | null
  created_at: string
  updated_at: string
}

export interface ChurnScoringBatch {
  id: number
  status: ChurnBatchStatus
  model_name: string
  model_schema_version: string
  model_version_id: number | null
  source_filename: string
  source_sha256: string
  source_system: string
  trigger_source: string
  observation_at: string | null
  decision_threshold: number
  medium_threshold: number
  row_count: number
  scored_count: number
  high_count: number
  medium_count: number
  low_count: number
  error_code: string | null
  drift_status: string
  drift: Record<string, unknown>
  started_at: string
  finished_at: string | null
  created_at: string
}

export interface ChurnScoringBatchList {
  items: ChurnScoringBatch[]
  total: number
}

export interface ChurnRiskPrediction {
  id: number
  student_external_id: string
  risk_score: number
  risk_level: ChurnRiskLevel
  predicted_churn: boolean
  risk_rank: number
  risk_percentile: number
  mapping_id: number | null
  student_id: number | null
  customer_id: number | null
  customer_name: string | null
  owner_id: number | null
  mapping_status: 'mapped' | 'unmapped'
  intervention: ChurnIntervention | null
  created_at: string
}

export interface ExternalStudentMapping {
  id: number
  source_system: string
  external_student_id: string
  student_id: number
  customer_id: number
  rebound_prediction_count: number
  created_at: string
}

export interface ChurnModelVersion {
  id: number
  version: string
  model_name: string
  schema_version: string
  artifact_filename: string
  artifact_sha256: string
  status: 'candidate' | 'approved' | 'retired'
  decision_threshold: number
  medium_threshold: number
  metrics: Record<string, unknown>
  approved_by: number | null
  approved_at: string | null
  created_at: string
}

export interface ChurnRiskBatchDetail {
  batch: ChurnScoringBatch
  items: ChurnRiskPrediction[]
  total: number
  page: number
  page_size: number
}
