<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { ChatMessage, ChatMessageCreate } from '../../types/chatMessage'

const props = defineProps<{ messages: ChatMessage[]; error?: string; sending?: boolean; suggestedDraft?: string; suggestedSuggestionId?: number | null }>()
const emit = defineEmits<{ send: [payload: ChatMessageCreate] }>()
const text = ref('')
const messagesElement = ref<HTMLElement | null>(null)
const parentPresets = [
  '您好，想了解一下初一数学课程和收费。',
  '孩子最近数学成绩不太稳定，老师有什么建议吗？',
  '这周末可以安排一次试听课吗？',
]

watch(() => props.suggestedDraft, (value) => {
  if (value !== undefined) text.value = value
})

watch(() => props.messages.length, async () => {
  // 新消息写入后保持在会话底部，符合聊天窗口的阅读习惯。
  await nextTick()
  if (messagesElement.value) messagesElement.value.scrollTop = messagesElement.value.scrollHeight
}, { immediate: true })

function send(): void {
  const content = text.value.trim()
  if (!content || props.sending) return
  emit('send', { wecom_message_id: `sidebar-${Date.now()}`, direction: 'outbound', message_type: 'text', content, suggestion_id: props.suggestedSuggestionId ?? undefined })
  text.value = ''
}

function simulateParentMessage(content: string, index: number): void {
  if (props.sending) return
  emit('send', { wecom_message_id: `parent-${Date.now()}-${index}`, direction: 'inbound', message_type: 'text', content })
}
</script>

<template>
  <section class="panel chat-panel">
    <div class="panel-heading"><div class="contact"><span class="contact-avatar">家</span><span><strong>客户会话</strong><small><i /> 本地 Mock 对话</small></span></div><button type="button" class="more" aria-label="会话选项">•••</button></div>
    <p v-if="error" class="error">{{ error }}</p>
    <div ref="messagesElement" class="messages">
      <p v-if="messages.length === 0" class="muted">暂无消息。</p>
      <article v-for="message in messages" :key="message.id" class="message" :class="message.direction">
        <span class="message-avatar">{{ message.direction === 'inbound' ? '家' : '我' }}</span><div class="bubble"><small>{{ message.direction === 'inbound' ? '客户' : '销售' }}</small><p>{{ message.content_masked || message.content || '[非文本消息]' }}</p><time>{{ new Date(message.sent_at).toLocaleString('zh-CN') }}</time></div>
      </article>
    </div>
    <div class="parent-presets">
      <span>本地模拟家长消息（仅用于测试）</span>
      <button v-for="(preset, index) in parentPresets" :key="preset" type="button" :disabled="sending" @click="simulateParentMessage(preset, index)">{{ preset }}</button>
    </div>
    <form class="composer" @submit.prevent="send">
      <textarea v-model="text" rows="3" placeholder="输入一条 Mock 消息…" />
      <button type="submit" :disabled="sending || !text.trim()">{{ sending ? '写入中…' : '人工确认后发送' }}</button>
    </form>
  </section>
</template>

<style scoped>
.panel { display: flex; min-height: 560px; flex-direction: column; padding: 0; border: 1px solid #dbe3f0; border-radius: 14px; background: white; }.panel-heading { display: flex; align-items: center; justify-content: space-between; padding: 14px 18px; border-bottom: 1px solid #e4e8ee; color: #172033; }.contact { display: flex; align-items: center; gap: 9px; }.contact-avatar, .message-avatar { display: grid; width: 31px; height: 31px; flex: 0 0 auto; place-items: center; border-radius: 10px; color: white; background: linear-gradient(135deg, #31c48d, #18a6c8); font-size: 12px; font-weight: 800; }.contact strong, .contact small { display: block; }.contact small { margin-top: 3px; color: #8895a8; font-size: 11px; font-weight: 400; }.contact i { display: inline-block; width: 6px; height: 6px; margin-right: 4px; border-radius: 50%; background: #07c160; }.more { padding: 4px 7px; border: 0; border-radius: 6px; color: #718096; background: transparent; cursor: pointer; }.more:hover { background: #edf1f5; }.muted { color: #64748b; }
.messages { flex: 1; overflow: auto; padding: 18px; }.message { display: flex; align-items: flex-start; gap: 7px; max-width: 88%; margin: 13px 0; }.message.outbound { flex-direction: row-reverse; margin-left: auto; }.message.outbound .message-avatar { color: #1d4ed8; background: #dbeafe; }.bubble { padding: 9px 12px; border-radius: 4px 13px 13px; background: white; box-shadow: 0 2px 8px rgb(15 23 42 / 8%); }.outbound .bubble { border-radius: 13px 4px 13px 13px; background: #b8f3c8; box-shadow: none; }.message small, .message time { color: #8190a4; font-size: 10px; }.message p { margin: 5px 0; color: #26354b; white-space: pre-wrap; line-height: 1.55; }
.parent-presets { display: grid; gap: 6px; margin: 0 16px; padding: 10px 0; border-top: 1px solid #e2e8f0; }.parent-presets span { color: #8b98aa; font-size: 11px; }.parent-presets button { padding: 6px 8px; border: 1px solid #d7e4f5; border-radius: 7px; color: #3b5b88; background: #f6faff; text-align: left; cursor: pointer; font-size: 12px; }.parent-presets button:disabled { opacity: .55; cursor: wait; }.composer { padding: 10px 16px 15px; border-top: 1px solid #e2e8f0; background: #fff; }.composer textarea { box-sizing: border-box; width: 100%; min-height: 64px; padding: 10px; border: 1px solid #d7dee8; border-radius: 8px; background: #fafcff; font: inherit; }.composer button { float: right; margin-top: 8px; padding: 8px 12px; border: 0; border-radius: 7px; color: white; background: #07c160; cursor: pointer; }.composer::after { display: table; clear: both; content: ''; }.composer button:disabled { opacity: .6; cursor: wait; }.error { padding: 0 16px; color: #b91c1c; }
</style>
