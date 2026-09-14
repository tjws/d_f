<script setup lang="ts">
import { ref } from 'vue'
import type { ChatMessage, ChatMessageCreate } from '../../types/chatMessage'
import type { TimelineEvent } from '../../types/timelineEvent'

const props = defineProps<{
  messages: ChatMessage[]
  timelineEvents: TimelineEvent[]
  chatError?: string
  timelineError?: string
}>()

const emit = defineEmits<{
  sendMessage: [payload: ChatMessageCreate]
}>()

const messageText = ref('')

function sendMessage(): void {
  const content = messageText.value.trim()
  if (!content) return

  emit('sendMessage', {
    wecom_message_id: `mock-${Date.now()}`,
    direction: 'inbound',
    message_type: 'text',
    content,
  })
  messageText.value = ''
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
        </div>

        <div class="composer">
          <textarea v-model="messageText" rows="3" placeholder="Mock 输入一条消息" />
          <button type="button" @click="sendMessage">写入 Mock 消息</button>
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

.error {
  color: #dc2626;
}

@media (max-width: 760px) {
  .columns {
    grid-template-columns: 1fr;
  }
}
</style>
