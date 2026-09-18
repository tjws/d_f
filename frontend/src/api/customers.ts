import { apiRequest } from './http'
import type {
  Customer,
  CustomerCreate,
  CustomerListResponse,
  CustomerStage,
  CustomerUpdate,
} from '../types/customer'
import type { CustomerTransfer } from '../types/customerTransfer'

export interface CustomerListParams {
  page?: number
  page_size?: number
  keyword?: string
  stage?: CustomerStage
}

export function listCustomers(
  params: CustomerListParams = {},
): Promise<CustomerListResponse> {
  const query = new URLSearchParams()

  query.set('page', String(params.page ?? 1))
  query.set('page_size', String(params.page_size ?? 20))

  if (params.keyword?.trim()) {
    query.set('keyword', params.keyword.trim())
  }

  if (params.stage) {
    query.set('stage', params.stage)
  }

  return apiRequest<CustomerListResponse>(`/customers?${query.toString()}`)
}

export function getCustomer(customerId: number): Promise<Customer> {
  return apiRequest<Customer>(`/customers/${customerId}`)
}

export function createCustomer(payload: CustomerCreate): Promise<Customer> {
  return apiRequest<Customer>('/customers', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateCustomer(
  customerId: number,
  payload: CustomerUpdate,
): Promise<Customer> {
  return apiRequest<Customer>(`/customers/${customerId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteCustomer(customerId: number): Promise<void> {
  return apiRequest<void>(`/customers/${customerId}`, {
    method: 'DELETE',
  })
}

export function transferCustomer(customerId: number, toUserId: number, reason?: string): Promise<Customer> {
  return apiRequest<Customer>(`/customers/${customerId}/owner`, {
    method: 'PATCH',
    body: JSON.stringify({ to_user_id: toUserId, reason: reason?.trim() || null }),
  })
}

export function listCustomerTransfers(customerId: number): Promise<CustomerTransfer[]> {
  return apiRequest<CustomerTransfer[]>(`/customers/${customerId}/transfers`)
}
