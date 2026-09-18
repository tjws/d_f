import type { AIEvidence } from './ai'

export interface Tag {
  id: number
  key: string
  name: string
  category: string
  description: string | null
  color: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface CustomerTag {
  id: number
  customer_id: number
  tag: Tag
  source: string
  status: string
  evidence: AIEvidence[]
  created_by: number | null
  confirmed_by: number | null
  created_at: string
  confirmed_at: string | null
}
