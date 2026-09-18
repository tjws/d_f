import { apiRequest } from './http'

export interface BusinessDashboardParams { start?: string; end?: string }

export interface BusinessDashboard {
  start: string
  end: string
  customer_total: number
  funnel: Array<{ stage: string; count: number }>
  orders: { total: number; by_status: Record<string, number>; paid_or_completed: number; paid_amount: number }
  tickets: { total: number; by_status: Record<string, number>; open_count: number }
  paying_customer_count: number
  repeat_purchase_customer_count: number
  renewal_rate: number
  renewal_rate_definition: string
  owner_efficiency: Array<{
    user_id: number
    username: string
    full_name: string | null
    customer_count: number
    converted_customer_count: number
    paid_amount: number
    open_ticket_count: number
  }>
}

export function getBusinessDashboard(params: BusinessDashboardParams = {}): Promise<BusinessDashboard> {
  const query = new URLSearchParams()
  if (params.start) query.set('start', params.start)
  if (params.end) query.set('end', params.end)
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return apiRequest<BusinessDashboard>(`/admin/business-dashboard${suffix}`)
}
