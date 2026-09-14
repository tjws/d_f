import { apiRequest } from './http'
import type {
  Organization,
  OrganizationCreate,
} from '../types/organization'

export function listOrganizations(): Promise<Organization[]> {
  return apiRequest<Organization[]>('/organizations')
}

export function createOrganization(
  payload: OrganizationCreate,
): Promise<Organization> {
  return apiRequest<Organization>('/organizations', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
