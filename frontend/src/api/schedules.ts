import { apiRequest } from './http'
import type { AISuggestion, AISuggestionUpdate } from '../types/aiSuggestion'
import type { Schedule, ScheduleUpdate } from '../types/schedule'

export function createScheduleSuggestion(
  customerId: number,
): Promise<AISuggestion> {
  return apiRequest<AISuggestion>(
    `/customers/${customerId}/schedule-suggestions`,
    { method: 'POST' },
  )
}

export function listScheduleSuggestions(
  customerId: number,
): Promise<AISuggestion[]> {
  return apiRequest<AISuggestion[]>(
    `/customers/${customerId}/schedule-suggestions`,
  )
}

export function updateScheduleSuggestion(
  customerId: number,
  suggestionId: number,
  payload: AISuggestionUpdate,
): Promise<AISuggestion> {
  return apiRequest<AISuggestion>(
    `/customers/${customerId}/schedule-suggestions/${suggestionId}`,
    { method: 'PATCH', body: JSON.stringify(payload) },
  )
}

export function confirmScheduleSuggestion(
  customerId: number,
  suggestionId: number,
): Promise<Schedule> {
  return apiRequest<Schedule>(
    `/customers/${customerId}/schedule-suggestions/${suggestionId}/confirm`,
    { method: 'POST' },
  )
}

export function listSchedules(customerId: number): Promise<Schedule[]> {
  return apiRequest<Schedule[]>(`/customers/${customerId}/schedules`)
}

export function updateSchedule(
  customerId: number,
  scheduleId: number,
  payload: ScheduleUpdate,
): Promise<Schedule> {
  return apiRequest<Schedule>(
    `/customers/${customerId}/schedules/${scheduleId}`,
    { method: 'PATCH', body: JSON.stringify(payload) },
  )
}

export function completeSchedule(
  customerId: number,
  scheduleId: number,
): Promise<Schedule> {
  return apiRequest<Schedule>(
    `/customers/${customerId}/schedules/${scheduleId}/complete`,
    { method: 'POST' },
  )
}

export function cancelSchedule(
  customerId: number,
  scheduleId: number,
): Promise<Schedule> {
  return apiRequest<Schedule>(
    `/customers/${customerId}/schedules/${scheduleId}/cancel`,
    { method: 'POST' },
  )
}
