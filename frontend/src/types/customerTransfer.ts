export interface CustomerTransfer {
  id: number
  customer_id: number
  from_user_id: number | null
  to_user_id: number | null
  operator_id: number | null
  reason: string | null
  created_at: string
}
