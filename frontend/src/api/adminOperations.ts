import { apiRequest } from './http'

export interface AdminOrder {
  id: number
  external_order_id: string
  customer_id: number
  customer_name: string
  owner_name: string | null
  course_name: string
  amount: string | number
  status: string
  ordered_at: string
}

export interface AdminTicket {
  id: number
  external_ticket_id: string
  customer_id: number
  customer_name: string
  owner_name: string | null
  type: string
  status: string
  summary: string
  opened_at: string
  closed_at: string | null
}

export interface AdminOperations {
  orders: AdminOrder[]
  tickets: AdminTicket[]
}

export interface OperationsSyncResult {
  customer_id: number
  orders_created: number
  orders_skipped: number
  tickets_created: number
  tickets_skipped: number
  provider: string
}

export function getAdminOperations(params: { order_status?: string; ticket_status?: string; limit?: number } = {}): Promise<AdminOperations> {
  const query = new URLSearchParams()
  if (params.order_status) query.set('order_status', params.order_status)
  if (params.ticket_status) query.set('ticket_status', params.ticket_status)
  if (params.limit) query.set('limit', String(params.limit))
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return apiRequest<AdminOperations>(`/admin/operations${suffix}`)
}

export function mockSyncOperations(payload: { customer_id: number; orders: unknown[]; tickets: unknown[] }): Promise<OperationsSyncResult> {
  return apiRequest<OperationsSyncResult>('/admin/operations/mock-sync', { method: 'POST', body: JSON.stringify(payload) })
}
