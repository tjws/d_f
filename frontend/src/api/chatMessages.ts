import { apiRequest } from './http'
import type {
  ChatMessage,
  ChatMessageCreate,
} from '../types/chatMessage'

export function listChatMessages(customerId: number): Promise<ChatMessage[]> {
  return apiRequest<ChatMessage[]>(`/customers/${customerId}/chat-messages`)
}

export function createMockChatMessage(
  customerId: number,
  payload: ChatMessageCreate,
): Promise<ChatMessage> {
  return apiRequest<ChatMessage>(
    `/customers/${customerId}/chat-messages/mock`,
    { method: 'POST', body: JSON.stringify(payload) },
  )
}
