import type { ChatMessage } from '../types/chatMessage'

/**
 * 聊天窗口按对话阅读顺序展示：较早的消息在上，最新消息在下。
 * 后端查询为了 AI 上下文可能返回“最新在前”，这里单独转换为 UI 顺序。
 */
export function sortChatMessagesForDisplay(messages: ChatMessage[]): ChatMessage[] {
  return [...messages].sort((left, right) => {
    const timeDifference = new Date(left.sent_at).getTime() - new Date(right.sent_at).getTime()
    return timeDifference || left.id - right.id
  })
}
