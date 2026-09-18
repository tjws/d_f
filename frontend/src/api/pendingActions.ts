import { apiRequest } from './http'
import type { PendingActionListResponse, PendingActionType } from '../types/pendingAction'

export type PendingActionDecision = 'accepted' | 'edited' | 'rejected'

export function listPendingActions(actionType?: PendingActionType): Promise<PendingActionListResponse> {
  const query = actionType ? `?action_type=${actionType}` : ''
  return apiRequest<PendingActionListResponse>(`/pending-actions${query}`)
}

export function decidePendingAction(
  actionType: PendingActionType,
  resourceId: number,
  action: PendingActionDecision,
  content?: Record<string, unknown>,
): Promise<{ action_type: PendingActionType; resource_id: number; action: PendingActionDecision; status: string; closed: boolean }> {
  return apiRequest(`/pending-actions/${actionType}/${resourceId}/decision`, {
    method: 'POST',
    body: JSON.stringify({ action, content }),
  })
}
