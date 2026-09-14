import { apiRequest } from './http'
import type {
  CustomerProfile,
  CustomerProfileUpdate,
} from '../types/customerProfile'

export function listCustomerProfiles(
  customerId: number,
): Promise<CustomerProfile[]> {
  return apiRequest<CustomerProfile[]>(`/customers/${customerId}/profiles`)
}

export function createCustomerProfileDraft(
  customerId: number,
): Promise<CustomerProfile> {
  return apiRequest<CustomerProfile>(
    `/customers/${customerId}/profiles/draft`,
    { method: 'POST' },
  )
}

export function updateCustomerProfile(
  customerId: number,
  profileId: number,
  payload: CustomerProfileUpdate,
): Promise<CustomerProfile> {
  return apiRequest<CustomerProfile>(
    `/customers/${customerId}/profiles/${profileId}`,
    { method: 'PATCH', body: JSON.stringify(payload) },
  )
}

export function confirmCustomerProfile(
  customerId: number,
  profileId: number,
): Promise<CustomerProfile> {
  return apiRequest<CustomerProfile>(
    `/customers/${customerId}/profiles/${profileId}/confirm`,
    { method: 'POST' },
  )
}

export function rejectCustomerProfile(
  customerId: number,
  profileId: number,
): Promise<CustomerProfile> {
  return apiRequest<CustomerProfile>(
    `/customers/${customerId}/profiles/${profileId}/reject`,
    { method: 'POST' },
  )
}
