export type ChatMessageDirection = 'inbound' | 'outbound'
export type ChatMessageType = 'text' | 'image' | 'voice' | 'file'

export interface ChatMessage {
  id: number
  customer_id: number
  user_id: number | null
  wecom_message_id: string
  direction: ChatMessageDirection
  message_type: ChatMessageType
  content: string | null
  content_masked: string | null
  media_object_key: string | null
  sent_at: string
  created_at: string
}

export interface ChatMessageCreate {
  wecom_message_id: string
  direction: ChatMessageDirection
  message_type?: ChatMessageType
  content?: string | null
  media_object_key?: string | null
  sent_at?: string | null
}
