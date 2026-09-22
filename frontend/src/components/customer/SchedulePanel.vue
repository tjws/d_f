<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { AISuggestion, AISuggestionUpdate } from '../../types/aiSuggestion'
import type { Schedule, ScheduleCompletion, ScheduleOutcome } from '../../types/schedule'

const props = defineProps<{
  suggestions: AISuggestion[]
  schedules: Schedule[]
  error?: string
}>()

const emit = defineEmits<{
  generate: []
  edit: [suggestionId: number, payload: AISuggestionUpdate]
  confirm: [suggestionId: number]
  complete: [scheduleId: number, payload: ScheduleCompletion]
  cancel: [scheduleId: number]
}>()

// 只有未处理的建议可编辑；已确认的建议已成为正式日程，不能继续作为草稿展示。
const actionableSuggestions = computed(() =>
  props.suggestions.filter((item) => item.status === 'draft' || item.status === 'edited'),
)
const currentSuggestion = computed(() => actionableSuggestions.value[0] ?? null)
const activeSchedules = computed(() => props.schedules.filter((item) => item.status === 'confirmed'))
const historySchedules = computed(() => props.schedules.filter((item) => item.status !== 'confirmed'))
const title = ref('')
const description = ref('')
const dueAt = ref('')
const priority = ref<'low' | 'normal' | 'high'>('normal')
const scheduleStatusLabels: Record<string, string> = {
  confirmed: '已确认',
  completed: '已完成',
  cancelled: '已取消',
}
const completingId = ref<number | null>(null)
const completionOutcome = ref<ScheduleOutcome>('contacted')
const completionNote = ref('')
const outcomeLabels: Record<ScheduleOutcome, string> = { contacted: '已联系', no_response: '未回应', appointment: '已预约', converted: '已成交', lost: '明确流失', other: '其他结果' }

function openCompletion(scheduleId: number): void {
  completingId.value = scheduleId
  completionOutcome.value = 'contacted'
  completionNote.value = ''
}

function submitCompletion(scheduleId: number): void {
  emit('complete', scheduleId, { outcome: completionOutcome.value, completion_note: completionNote.value.trim() || null })
  completingId.value = null
}

function toDateTimeLocal(value: unknown): string {
  if (typeof value !== 'string' || !value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('zh-CN')
}

watch(
  currentSuggestion,
  (suggestion) => {
    const content = suggestion?.edited_content ?? suggestion?.content
    title.value = String(content?.title ?? '')
    description.value = String(content?.description ?? '')
    dueAt.value = toDateTimeLocal(content?.due_at)
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

    <div v-if="currentSuggestion" class="suggestion">
      <p class="suggestion-note">AI 建议，请确认内容与时间后再创建正式日程。</p>
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
        type="button"
        class="success"
        @click="emit('confirm', currentSuggestion.id)"
      >
        确认生成正式日程
      </button>
    </div>

    <p v-if="!currentSuggestion" class="muted">
      暂无待确认日程建议。你可以按需要生成新的跟进建议。
    </p>

    <h3>当前正式日程</h3>
    <div v-for="schedule in activeSchedules" :key="schedule.id" class="schedule">
      <div>
        <strong>{{ schedule.title }}</strong>
        <p>{{ formatDateTime(schedule.due_at) }} · {{ schedule.priority }} · {{ scheduleStatusLabels[schedule.status] ?? schedule.status }}</p>
        <p v-if="schedule.status === 'completed'" class="completion-summary">人工结果：{{ outcomeLabels[schedule.outcome as ScheduleOutcome] ?? schedule.outcome ?? '其他结果' }}<span v-if="schedule.completion_note"> · {{ schedule.completion_note }}</span></p>
      </div>
      <div class="actions" v-if="schedule.status === 'confirmed'">
        <button type="button" class="success" @click="openCompletion(schedule.id)">
          记录结果
        </button>
        <button type="button" class="danger" @click="emit('cancel', schedule.id)">
          取消
        </button>
      </div>
      <form v-if="completingId === schedule.id" class="completion-form" @submit.prevent="submitCompletion(schedule.id)">
        <label>跟进结果<select v-model="completionOutcome"><option v-for="(label, value) in outcomeLabels" :key="value" :value="value">{{ label }}</option></select></label>
        <label>备注（可选）<input v-model="completionNote" maxlength="500" placeholder="例如：已约好周末试听" /></label>
        <div><button type="submit" class="success">保存结果并完成</button><button type="button" class="secondary" @click="completingId = null">取消</button></div>
      </form>
    </div>

    <p v-if="activeSchedules.length === 0" class="muted">
      暂无正式日程。
    </p>

    <details v-if="historySchedules.length" class="schedule-history">
      <summary>已完成或已取消的历史日程（{{ historySchedules.length }}）</summary>
      <div v-for="schedule in historySchedules" :key="schedule.id" class="history-item">
        <strong>{{ schedule.title }}</strong>
        <span>{{ formatDateTime(schedule.due_at) }} · {{ scheduleStatusLabels[schedule.status] ?? '已处理' }}</span>
      </div>
    </details>
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
.suggestion-note { color: #9a3412 !important; font-size: 13px; }

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

.completion-form { display: grid; gap: 7px; width: 100%; margin-top: 10px; padding-top: 10px; border-top: 1px solid #fed7aa; }
.secondary { margin-left: 8px; color: #475569; background: #e2e8f0; }
.schedule-history { margin-top: 18px; padding-top: 14px; border-top: 1px solid #e2e8f0; color: #64748b; font-size: 13px; }.schedule-history summary { cursor: pointer; font-weight: 600; }.history-item { display: grid; gap: 4px; margin-top: 9px; padding: 9px; border-radius: 8px; background: #f8fafc; }.history-item span { font-size: 12px; }
</style>
