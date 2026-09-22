<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type {
  AISuggestion,
  AISuggestionUpdate,
} from '../../types/aiSuggestion'

const props = defineProps<{
  suggestions: AISuggestion[]
  error?: string
}>()

const emit = defineEmits<{
  generate: []
  edit: [suggestionId: number, payload: AISuggestionUpdate]
  accept: [suggestionId: number]
  reject: [suggestionId: number]
  use: [suggestionId: number, text: string]
}>()

const currentSuggestion = computed(
  () => props.suggestions[0] ?? null,
)
const text = ref('')
const suggestionStatusLabels: Record<string, string> = {
  draft: '草稿待审阅',
  edited: '已人工编辑',
  accepted: '已人工接受',
  rejected: '已拒绝',
  expired: '已过期',
}

watch(
  currentSuggestion,
  (suggestion) => {
    text.value = String(
      suggestion?.edited_content?.text ?? suggestion?.content.text ?? '',
    )
  },
  { immediate: true },
)

function saveEdit(): void {
  if (!currentSuggestion.value) return

  emit('edit', currentSuggestion.value.id, {
    content: {
      ...currentSuggestion.value.content,
      text: text.value,
    },
  })
}

function useSuggestion(): void {
  if (!currentSuggestion.value || !text.value.trim()) return
  emit('use', currentSuggestion.value.id, text.value.trim())
}
</script>

<template>
  <section class="panel">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">AI Reply Suggestion</p>
        <h2>回复建议</h2>
      </div>
      <button type="button" @click="emit('generate')">
        {{ currentSuggestion ? '重新生成建议' : '生成建议' }}
      </button>
    </div>

    <p v-if="props.error" class="error">{{ props.error }}</p>
    <p v-if="!currentSuggestion" class="muted">
      暂无回复建议。建议先确认客户画像。
    </p>

    <template v-else>
      <div class="status-row">
        <span>{{ suggestionStatusLabels[currentSuggestion.status] ?? currentSuggestion.status }}</span>
        <span>生成于 {{ new Date(currentSuggestion.created_at).toLocaleString('zh-CN') }}</span>
      </div>

      <label class="suggestion-editor">建议内容（可直接修改）<textarea v-model="text" rows="5" :disabled="currentSuggestion.status === 'rejected'" /></label>

      <div class="actions">
        <template v-if="currentSuggestion.status === 'draft' || currentSuggestion.status === 'edited'">
          <button type="button" @click="saveEdit">保存编辑</button>
          <button type="button" class="success" @click="emit('accept', currentSuggestion.id)">接受建议</button>
          <button type="button" class="danger" @click="emit('reject', currentSuggestion.id)">拒绝建议</button>
        </template>
        <button
          v-else-if="currentSuggestion.status === 'accepted'"
          type="button"
          class="success"
          @click="useSuggestion"
        >
          放入聊天输入框
        </button>
      </div>

      <p class="human-note">
        {{ currentSuggestion.status === 'accepted' ? '下一步：放入聊天输入框后，请再次核对内容，再由你手动发送。' : '接受建议不会自动发送消息，发送动作仍由人工完成。' }}
      </p>

    </template>
  </section>
</template>

<style scoped>
.panel {
  padding: 22px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: white;
}

.panel-heading,
.status-row,
.actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.eyebrow {
  margin: 0 0 6px;
  color: #7c3aed;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

h2 {
  margin: 0 0 16px;
}

textarea {
  box-sizing: border-box;
  width: 100%;
  margin: 16px 0 8px;
  padding: 10px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font: inherit;
}
.suggestion-editor { display: grid; gap: 6px; margin-top: 16px; color: #475569; font-size: 13px; font-weight: 700; }

button {
  padding: 8px 12px;
  border: 0;
  border-radius: 8px;
  color: white;
  background: #7c3aed;
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.success {
  background: #16a34a;
}

.danger {
  background: #dc2626;
}

.muted,
.status-row,
.human-note {
  color: #64748b;
}

.error {
  color: #dc2626;
}

.human-note {
  margin-bottom: 0;
  font-size: 13px;
}
</style>
