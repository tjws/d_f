export type SalesScriptStatus = 'draft' | 'pending_review' | 'published' | 'disabled'

export interface SalesScript {
  id: number
  scene: string
  customer_stage: string | null
  objection_type: string | null
  title: string
  content: string
  tone: string | null
  status: SalesScriptStatus
  version: number
  created_by: number | null
  approved_by: number | null
  created_at: string
  updated_at: string
}

export interface SalesScriptCreate {
  scene: string
  customer_stage?: string | null
  objection_type?: string | null
  title: string
  content: string
  tone?: string | null
}

export interface SalesScriptUpdate extends Partial<SalesScriptCreate> {
  status?: SalesScriptStatus
}
