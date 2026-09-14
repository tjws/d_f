import { apiRequest } from './http'
import type {
  AISuggestion,
  AISuggestionUpdate,
} from '../types/aiSuggestion'

export function listAISuggestions(customerId: number): Promise<AISuggestion[]> {
  return apiRequest<AISuggestion[]>(`/customers/${customerId}/suggestions`)
}

export function createReplyDraft(customerId: number): Promise<AISuggestion> {
  return apiRequest<AISuggestion>(
    `/customers/${customerId}/suggestions/reply-draft`,
    { method: 'POST' },
  )
}

export function updateAISuggestion(
  customerId: number,
  suggestionId: number,
  payload: AISuggestionUpdate,
): Promise<AISuggestion> {
  return apiRequest<AISuggestion>(
    `/customers/${customerId}/suggestions/${suggestionId}`,
    { method: 'PATCH', body: JSON.stringify(payload) },
  )
}

export function acceptAISuggestion(
  customerId: number,
  suggestionId: number,
): Promise<AISuggestion> {
  return apiRequest<AISuggestion>(
    `/customers/${customerId}/suggestions/${suggestionId}/accept`,
    { method: 'POST' },
  )
}

export function rejectAISuggestion(
  customerId: number,
  suggestionId: number,
): Promise<AISuggestion> {
  return apiRequest<AISuggestion>(
    `/customers/${customerId}/suggestions/${suggestionId}/reject`,
    { method: 'POST' },
  )
}
