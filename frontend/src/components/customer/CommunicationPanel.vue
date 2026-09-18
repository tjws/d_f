<script setup lang="ts">
import { ref } from 'vue'
import type { ChatMessage, ChatMessageCreate, ChatMessageDirection, ChatMessageType } from '../../types/chatMessage'
import type { TimelineEvent, TimelineEventCreate } from '../../types/timelineEvent'

const props = defineProps<{
  messages: ChatMessage[]
  timelineEvents: TimelineEvent[]
  chatError?: string
  timelineError?: string
}>()

const emit = defineEmits<{
  sendMessage: [payload: ChatMessageCreate]
  transcribeMessage: [messageId: number]
  createTimelineEvent: [payload: TimelineEventCreate]
}>()

const messageText = ref('')
const messageDirection = ref<ChatMessageDirection>('inbound')
const messageType = ref<ChatMessageType>('text')
const mediaObjectKey = ref('')
const timelineEventType = ref('manual_follow_up')
const timelineSummary = ref('')

function sendMessage(): void {
  const content = messageText.value.trim()
  if (messageType.value === 'text' && !content) return
  if (messageType.value !== 'text' && !mediaObjectKey.value.trim()) return

  emit('sendMessage', {
    wecom_message_id: `mock-${Date.now()}`,
    direction: messageDirection.value,
    message_type: messageType.value,
    content: content || null,
    media_object_key: mediaObjectKey.value.trim() || null,
  })
  messageText.value = ''
  mediaObjectKey.value = ''
}

function createTimelineEvent(): void {
  const summary = timelineSummary.value.trim()
  if (!summary) return
  emit('createTimelineEvent', {
    event_type: timelineEventType.value,
    summary,
  })
  timelineSummary.value = ''
}
</script>

<template>
  <section class="panel communication-panel">
    <div class="columns">
      <div>
        <p class="eyebrow">Chat</p>
        <h2>聊天消息</h2>
        <p v-if="props.chatError" class="error">{{ props.chatError }}</p>
        <p v-if="props.messages.length === 0" class="muted">暂无聊天记录。</p>
        <div v-for="message in props.messages" :key="message.id" class="message">
          <strong>{{ message.direction === 'inbound' ? '客户' : '销售' }}</strong>
          <p>{{ message.content_masked || message.content || '[非文本消息]' }}</p>
          <small>{{ message.sent_at }}</small>
          <button v-if="message.message_type === 'voice' && !message.content" type="button" class="inline-button" @click="emit('transcribeMessage', message.id)">Mock 转写</button>
        </div>

        <div class="composer">
          <label>消息方向
            <select v-model="messageDirection">
              <option value="inbound">客户发来</option>
              <option value="outbound">销售发送</option>
            </select>
          </label>
          <label>消息类型
            <select v-model="messageType">
              <option value="text">文本</option>
              <option value="voice">语音（Mock 媒体）</option>
              <option value="image">图片（仅索引）</option>
              <option value="file">文件（仅索引）</option>
            </select>
          </label>
          <textarea v-model="messageText" rows="3" placeholder="Mock 输入一条消息" />
          <input v-if="messageType !== 'text'" v-model="mediaObjectKey" placeholder="媒体对象 key，例如 mock-voice:家长想了解课程" />
          <button type="button" :disabled="messageType === 'text' ? !messageText.trim() : !mediaObjectKey.trim()" @click="sendMessage">写入 Mock 消息</button>
        </div>
      </div>

      <div>
        <p class="eyebrow">Timeline</p>
        <h2>时间线</h2>
        <p v-if="props.timelineError" class="error">{{ props.timelineError }}</p>
        <p v-if="props.timelineEvents.length === 0" class="muted">暂无时间线事件。</p>
        <div v-for="event in props.timelineEvents" :key="event.id" class="event">
          <strong>{{ event.event_type }}</strong>
          <p>{{ event.summary }}</p>
          <small>{{ event.occurred_at }}</small>
        </div>
        <div class="composer">
          <label>事件类型
            <input v-model="timelineEventType" maxlength="50" />
          </label>
          <textarea v-model="timelineSummary" rows="3" placeholder="记录一次人工跟进、电话或备注" />
          <button type="button" :disabled="!timelineSummary.trim()" @click="createTimelineEvent">新增时间线事件</button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.panel {
  padding: 22px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: white;
}

.columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
}

.eyebrow {
  margin: 0 0 6px;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

h2 {
  margin: 0 0 16px;
}

.message,
.event {
  margin-bottom: 10px;
  padding: 12px;
  border-radius: 10px;
  background: #f8fafc;
}

.message p,
.event p {
  margin: 5px 0;
}

small,
.muted {
  color: #64748b;
}

.composer {
  margin-top: 16px;
}

label {
  display: block;
  margin-bottom: 8px;
  color: #475569;
  font-size: 13px;
}

select,
input {
  box-sizing: border-box;
  width: 100%;
  margin-top: 5px;
  padding: 8px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: white;
  font: inherit;
}

textarea {
  box-sizing: border-box;
  width: 100%;
  margin-bottom: 8px;
  padding: 10px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font: inherit;
}

button {
  padding: 8px 12px;
  border: 0;
  border-radius: 8px;
  color: white;
  background: #475569;
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.inline-button {
  margin-top: 6px;
  padding: 5px 8px;
  font-size: 12px;
  background: #2563eb;
}

.error {
  color: #dc2626;
}

@media (max-width: 760px) {
  .columns {
    grid-template-columns: 1fr;
  }
}
</style>
