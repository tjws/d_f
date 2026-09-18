<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { AISuggestion, AISuggestionUpdate } from '../../types/aiSuggestion'
import type { CustomerTag } from '../../types/tag'
import type { Schedule, ScheduleCompletion, ScheduleOutcome } from '../../types/schedule'
import AIEvidencePanel from '../ai/AIEvidencePanel.vue'

const props = defineProps<{
  tags: CustomerTag[]
  scheduleSuggestions: AISuggestion[]
  schedules: Schedule[]
  busy?: boolean
  error?: string
}>()

const emit = defineEmits<{
  generateTags: []
  confirmTag: [id: number]
  rejectTag: [id: number]
  generateSchedule: []
  editSchedule: [id: number, payload: AISuggestionUpdate]
  confirmSchedule: [id: number]
  completeSchedule: [id: number, payload: ScheduleCompletion]
  cancelSchedule: [id: number]
}>()

const currentScheduleSuggestion = computed(() => props.scheduleSuggestions[0] ?? null)
const title = ref('')
const description = ref('')
const dueAt = ref('')
const completingId = ref<number | null>(null)
const completionOutcome = ref<ScheduleOutcome>('contacted')
const completionNote = ref('')
const outcomeLabels: Record<ScheduleOutcome, string> = { contacted: '已联系', no_response: '未回应', appointment: '已预约', converted: '已成交', lost: '明确流失', other: '其他结果' }

watch(currentScheduleSuggestion, (suggestion) => {
  const content = suggestion?.edited_content ?? suggestion?.content
  title.value = String(content?.title ?? '')
  description.value = String(content?.description ?? '')
  dueAt.value = String(content?.due_at ?? '')
}, { immediate: true })

function saveScheduleEdit(): void {
  const suggestion = currentScheduleSuggestion.value
  if (!suggestion || !title.value.trim() || !dueAt.value) return
  emit('editSchedule', suggestion.id, {
    content: { ...(suggestion.edited_content ?? suggestion.content), title: title.value.trim(), description: description.value.trim(), due_at: dueAt.value },
  })
}

function openCompletion(scheduleId: number): void { completingId.value = scheduleId; completionOutcome.value = 'contacted'; completionNote.value = '' }
function submitCompletion(scheduleId: number): void {
  emit('completeSchedule', scheduleId, { outcome: completionOutcome.value, completion_note: completionNote.value.trim() || null })
  completingId.value = null
}
</script>

<template>
  <section class="panel planning-panel">
    <div class="panel-heading"><span>标签与日程</span><small>人工确认</small></div>
    <p v-if="props.error" class="error">{{ props.error }}</p>

    <div class="planning-block">
      <div class="block-title"><strong>AI 标签</strong><button type="button" :disabled="props.busy" @click="emit('generateTags')">生成标签</button></div>
      <p v-if="props.tags.length === 0" class="muted">暂无标签建议。</p>
      <article v-for="item in props.tags" :key="item.id" class="tag-item">
        <span><strong>{{ item.tag.name }}</strong> · {{ item.status }}</span>
        <div v-if="item.status === 'suggested'" class="actions"><button type="button" class="success" @click="emit('confirmTag', item.id)">确认</button><button type="button" class="danger" @click="emit('rejectTag', item.id)">拒绝</button></div>
      </article>
    </div>

    <div class="planning-block">
      <div class="block-title"><strong>AI 日程</strong><button type="button" :disabled="props.busy" @click="emit('generateSchedule')">生成日程</button></div>
      <p v-if="!currentScheduleSuggestion" class="muted">暂无日程建议。</p>
      <div v-else class="schedule-suggestion">
        <label>标题<input v-model="title" /></label>
        <label>说明<textarea v-model="description" rows="2" /></label>
        <label>截止时间<input v-model="dueAt" type="datetime-local" /></label>
        <div class="actions"><button type="button" @click="saveScheduleEdit">保存编辑</button><button v-if="currentScheduleSuggestion.status === 'draft' || currentScheduleSuggestion.status === 'edited'" type="button" class="success" @click="emit('confirmSchedule', currentScheduleSuggestion.id)">确认日程</button></div>
        <AIEvidencePanel :evidence="currentScheduleSuggestion.evidence" />
      </div>
      <article v-for="schedule in props.schedules" :key="schedule.id" class="schedule-item">
        <span><strong>{{ schedule.title }}</strong><small>{{ schedule.due_at }} · {{ schedule.status }}</small><small v-if="schedule.status === 'completed'">人工结果：{{ outcomeLabels[schedule.outcome as ScheduleOutcome] ?? schedule.outcome ?? '其他结果' }}<template v-if="schedule.completion_note"> · {{ schedule.completion_note }}</template></small></span>
        <div v-if="schedule.status === 'confirmed'" class="actions"><button type="button" class="success" @click="openCompletion(schedule.id)">记录结果</button><button type="button" class="danger" @click="emit('cancelSchedule', schedule.id)">取消</button></div>
        <form v-if="completingId === schedule.id" class="completion-form" @submit.prevent="submitCompletion(schedule.id)">
          <label>跟进结果<select v-model="completionOutcome"><option v-for="(label, value) in outcomeLabels" :key="value" :value="value">{{ label }}</option></select></label>
          <label>备注（可选）<input v-model="completionNote" maxlength="500" placeholder="例如：已约好周末试听" /></label>
          <div class="actions"><button type="submit" class="success">保存并完成</button><button type="button" @click="completingId = null">取消</button></div>
        </form>
      </article>
    </div>
  </section>
</template>

<style scoped>
.panel { padding: 16px; border: 1px solid #dbe3f0; border-radius: 14px; background: rgb(255 255 255 / 94%); box-shadow: 0 8px 22px rgb(30 64 175 / 5%); }
.panel-heading, .block-title, .tag-item, .schedule-item, .actions { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.panel-heading { margin-bottom: 12px; color: #1e3a8a; font-weight: 700; }.panel-heading small, .muted { color: #64748b; font-weight: 400; }
.planning-block { display: grid; gap: 8px; padding-top: 10px; margin-top: 10px; border-top: 1px solid #e2e8f0; }.block-title strong { color: #334155; }
button { padding: 7px 9px; border: 0; border-radius: 7px; color: white; background: #2563eb; cursor: pointer; }button:disabled { opacity: .5; cursor: not-allowed; }.success { background: #16a34a; }.danger { background: #be123c; }
.tag-item, .schedule-item, .schedule-suggestion { padding: 9px; border-radius: 8px; background: #f8fafc; }.tag-item strong { color: #0f766e; }.schedule-item { align-items: flex-start; }.schedule-item span { display: grid; gap: 3px; }.schedule-item small { color: #64748b; }
label { display: grid; gap: 4px; color: #475569; font-size: 12px; }input, textarea { box-sizing: border-box; width: 100%; padding: 7px; border: 1px solid #cbd5e1; border-radius: 7px; font: inherit; }
.completion-form { display: grid; gap: 7px; width: 100%; padding-top: 8px; border-top: 1px solid #dbe3f0; }.completion-form select { box-sizing: border-box; width: 100%; padding: 7px; border: 1px solid #cbd5e1; border-radius: 7px; font: inherit; }
.error { color: #b91c1c; }
</style>
