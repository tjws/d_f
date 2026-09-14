<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { AISuggestion, AISuggestionUpdate } from '../../types/aiSuggestion'
import type { Schedule } from '../../types/schedule'

const props = defineProps<{
  suggestions: AISuggestion[]
  schedules: Schedule[]
  error?: string
}>()

const emit = defineEmits<{
  generate: []
  edit: [suggestionId: number, payload: AISuggestionUpdate]
  confirm: [suggestionId: number]
  complete: [scheduleId: number]
  cancel: [scheduleId: number]
}>()

const currentSuggestion = computed(() => props.suggestions[0] ?? null)
const title = ref('')
const description = ref('')
const dueAt = ref('')
const priority = ref<'low' | 'normal' | 'high'>('normal')

watch(
  currentSuggestion,
  (suggestion) => {
    const content = suggestion?.edited_content ?? suggestion?.content
    title.value = String(content?.title ?? '')
    description.value = String(content?.description ?? '')
    dueAt.value = String(content?.due_at ?? '')
    const value = String(content?.priority ?? 'normal')
    priority.value = value === 'low' || value === 'high' ? value : 'normal'
  },
  { immediate: true },
)

function saveSuggestion(): void {
  if (!currentSuggestion.value) return

  emit('edit', currentSuggestion.value.id, {
    content: {
      ...(currentSuggestion.value.edited_content ?? currentSuggestion.value.content),
      title: title.value,
      description: description.value,
      due_at: dueAt.value,
      priority: priority.value,
    },
  })
}
</script>

<template>
  <section class="panel">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">AI Follow-up</p>
        <h2>跟进日程</h2>
      </div>
      <button type="button" @click="emit('generate')">
        生成日程建议
      </button>
    </div>

    <p v-if="props.error" class="error">{{ props.error }}</p>

    <div v-for="item in props.suggestions" :key="item.id" class="suggestion">
      <label>
        标题
        <input v-model="title" type="text" />
      </label>
      <label>
        说明
        <textarea v-model="description" rows="2" />
      </label>
      <label>
        截止时间
        <input v-model="dueAt" type="datetime-local" />
      </label>
      <label>
        优先级
        <select v-model="priority">
          <option value="low">低</option>
          <option value="normal">普通</option>
          <option value="high">高</option>
        </select>
      </label>
      <button type="button" @click="saveSuggestion">保存编辑</button>
      <button
        v-if="item.status === 'draft' || item.status === 'edited'"
        type="button"
        class="success"
        @click="emit('confirm', item.id)"
      >
        确认生成正式日程
      </button>
    </div>

    <p v-if="props.suggestions.length === 0" class="muted">
      暂无日程建议。
    </p>

    <h3>正式日程</h3>
    <div v-for="schedule in props.schedules" :key="schedule.id" class="schedule">
      <div>
        <strong>{{ schedule.title }}</strong>
        <p>{{ schedule.due_at }} · {{ schedule.priority }} · {{ schedule.status }}</p>
      </div>
      <div class="actions" v-if="schedule.status === 'confirmed'">
        <button type="button" class="success" @click="emit('complete', schedule.id)">
          完成
        </button>
        <button type="button" class="danger" @click="emit('cancel', schedule.id)">
          取消
        </button>
      </div>
    </div>

    <p v-if="props.schedules.length === 0" class="muted">
      暂无正式日程。
    </p>
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
.schedule,
.actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.eyebrow {
  margin: 0 0 6px;
  color: #ea580c;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

h2 {
  margin: 0 0 16px;
}

h3 {
  margin-top: 24px;
  padding-top: 18px;
  border-top: 1px solid #e2e8f0;
}

button {
  padding: 8px 12px;
  border: 0;
  border-radius: 8px;
  color: white;
  background: #ea580c;
  cursor: pointer;
}

.success {
  background: #16a34a;
}

.danger {
  background: #dc2626;
}

.suggestion,
.schedule {
  margin-top: 10px;
  padding: 12px;
  border-radius: 10px;
  background: #fff7ed;
}

.suggestion p,
.schedule p {
  margin: 6px 0;
  color: #64748b;
}

label {
  display: block;
  margin: 8px 0;
  color: #475569;
  font-size: 13px;
  font-weight: 600;
}

input,
textarea,
select {
  box-sizing: border-box;
  width: 100%;
  margin-top: 4px;
  padding: 8px;
  border: 1px solid #fed7aa;
  border-radius: 8px;
  font: inherit;
}

.muted {
  color: #64748b;
}

.error {
  color: #dc2626;
}
</style>
