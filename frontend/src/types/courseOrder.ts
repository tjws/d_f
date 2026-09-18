export type CourseOrderStatus = 'intent' | 'pending_payment' | 'paid' | 'cancelled' | 'completed'

export interface CourseOrder {
  id: number
  external_order_id: string
  customer_id: number
  student_id: number | null
  course_name: string
  amount: string
  status: CourseOrderStatus
  ordered_at: string
  raw_snapshot: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface CourseOrderCreate {
  external_order_id: string
  student_id?: number | null
  course_name: string
  amount: string
  status?: CourseOrderStatus
}

export interface CourseOrderUpdate {
  course_name?: string
  amount?: string
  status?: CourseOrderStatus
  student_id?: number | null
}
