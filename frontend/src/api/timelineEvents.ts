import { apiRequest } from './http'
import type {
  TimelineEvent,
  TimelineEventCreate,
} from '../types/timelineEvent'

export function listTimelineEvents(
  customerId: number,
): Promise<TimelineEvent[]> {
  return apiRequest<TimelineEvent[]>(
    `/customers/${customerId}/timeline-events`,
  )
}

export function createTimelineEvent(
  customerId: number,
  payload: TimelineEventCreate,
): Promise<TimelineEvent> {
  return apiRequest<TimelineEvent>(
    `/customers/${customerId}/timeline-events`,
    { method: 'POST', body: JSON.stringify(payload) },
  )
}
