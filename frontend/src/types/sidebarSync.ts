import type { ChatMessage } from './chatMessage'
import type { TimelineEvent } from './timelineEvent'

export interface SidebarSyncResponse {
  messages: ChatMessage[]
  timeline_events: TimelineEvent[]
  next_message_id: number
  next_timeline_id: number
}
