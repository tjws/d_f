export interface Student {
  id: number
  customer_id: number
  name: string
  gender: string | null
  grade: string | null
  school: string | null
  birth_date: string | null
  subjects: Record<string, unknown> | null
  created_at: string
  updated_at: string
  archived_at: string | null
}

export interface StudentUpdate {
  name?: string
  gender?: string | null
  grade?: string | null
  school?: string | null
  birth_date?: string | null
  subjects?: Record<string, unknown> | null
}

export interface StudentCreate {
  name: string
  gender?: string | null
  grade?: string | null
  school?: string | null
  birth_date?: string | null
  subjects?: Record<string, unknown> | null
}
