import { apiRequest } from './http'
import type { SidebarSyncResponse } from '../types/sidebarSync'

export function syncSidebarCustomer(
  customerId: number,
  afterMessageId: number,
  afterTimelineId: number,
): Promise<SidebarSyncResponse> {
  const params = new URLSearchParams({
    after_message_id: String(afterMessageId),
    after_timeline_id: String(afterTimelineId),
  })
  return apiRequest<SidebarSyncResponse>(`/customers/${customerId}/sidebar-sync?${params.toString()}`)
}
