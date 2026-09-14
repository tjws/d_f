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
}>()

const currentSuggestion = computed(
  () => props.suggestions[0] ?? null,
)
const text = ref('')

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
</script>

<template>
  <section class="panel">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">AI Reply Suggestion</p>
        <h2>回复建议</h2>
      </div>
      <button type="button" @click="emit('generate')">
        生成建议
      </button>
    </div>

    <p v-if="props.error" class="error">{{ props.error }}</p>
    <p v-if="!currentSuggestion" class="muted">
      暂无回复建议。建议先确认客户画像。
    </p>

    <template v-else>
      <div class="status-row">
        <span>状态：{{ currentSuggestion.status }}</span>
        <span>证据等级：{{ currentSuggestion.evidence_level }}</span>
      </div>

      <textarea v-model="text" rows="5" />

      <div class="actions">
        <button type="button" @click="saveEdit">保存编辑</button>
        <button
          type="button"
          class="success"
          :disabled="currentSuggestion.status !== 'draft' && currentSuggestion.status !== 'edited'"
          @click="emit('accept', currentSuggestion.id)"
        >
          接受建议
        </button>
        <button
          type="button"
          class="danger"
          :disabled="currentSuggestion.status !== 'draft' && currentSuggestion.status !== 'edited'"
          @click="emit('reject', currentSuggestion.id)"
        >
          拒绝建议
        </button>
      </div>

      <p class="human-note">
        接受建议不会自动发送消息，发送动作仍由人工完成。
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
