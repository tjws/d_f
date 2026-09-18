import { apiRequest } from './http'
import type { ChatMessageCreate } from '../types/chatMessage'

export interface MockCallbackPayload extends ChatMessageCreate {
  event_id: string
  event_type: 'chat_message'
  userid: string
  customer_id: number
}

export function emitMockCallback(payload: MockCallbackPayload): Promise<{ event_id: string; status: string }> {
  return apiRequest<{ event_id: string; status: string }>(
    '/wecom/mock/emit',
    { method: 'POST', body: JSON.stringify(payload) },
  )
}
