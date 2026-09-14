import { apiRequest } from './http'
import type { CustomerTag, Tag } from '../types/tag'

export function listTags(): Promise<Tag[]> {
  return apiRequest<Tag[]>('/tags')
}

export function suggestCustomerTags(customerId: number): Promise<CustomerTag[]> {
  return apiRequest<CustomerTag[]>(
    `/customers/${customerId}/tags/suggestions`,
    { method: 'POST' },
  )
}

export function listCustomerTags(customerId: number): Promise<CustomerTag[]> {
  return apiRequest<CustomerTag[]>(`/customers/${customerId}/tags`)
}

export function confirmCustomerTag(
  customerId: number,
  customerTagId: number,
): Promise<CustomerTag> {
  return apiRequest<CustomerTag>(
    `/customers/${customerId}/tags/${customerTagId}/confirm`,
    { method: 'POST' },
  )
}

export function rejectCustomerTag(
  customerId: number,
  customerTagId: number,
): Promise<CustomerTag> {
  return apiRequest<CustomerTag>(
    `/customers/${customerId}/tags/${customerTagId}/reject`,
    { method: 'POST' },
  )
}
