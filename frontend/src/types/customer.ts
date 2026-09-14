export type CustomerStage =
  | 'new'
  | 'following_up'
  | 'converted'
  | 'lost'

export interface Customer {
  id: number
  owner_id: number | null

  name: string
  phone: string
  student_name: string | null
  grade: string | null
  interested_subject: string | null

  stage: CustomerStage
  source: string | null
  remark: string | null
  next_follow_up_at: string | null

  created_at: string
  updated_at: string
}

export interface CustomerCreate {
  name: string
  phone: string
  student_name?: string | null
  grade?: string | null
  interested_subject?: string | null
  stage?: CustomerStage
  source?: string | null
  remark?: string | null
  next_follow_up_at?: string | null
}

export interface CustomerUpdate {
  name?: string
  phone?: string
  student_name?: string | null
  grade?: string | null
  interested_subject?: string | null
  stage?: CustomerStage
  source?: string | null
  remark?: string | null
  next_follow_up_at?: string | null
}

export interface CustomerListResponse {
  items: Customer[]
  total: number
  page: number
  page_size: number
}