<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Customer } from '../../types/customer'
import type { CustomerProfile } from '../../types/customerProfile'
import type { AISuggestion, AISuggestionUpdate } from '../../types/aiSuggestion'
import type { TimelineEvent } from '../../types/timelineEvent'
import type { Student } from '../../types/student'

const props = defineProps<{ customer: Customer | null; profile: CustomerProfile | null; students: Student[]; suggestions: AISuggestion[]; timelineEvents: TimelineEvent[]; busy?: boolean; notice?: string; error?: string }>()
const emit = defineEmits<{ run: []; confirmProfile: [id: number]; edit: [id: number, payload: AISuggestionUpdate]; useSuggestion: [id: number, text: string]; accept: [id: number]; reject: [id: number] }>()
// 已发送的建议不应继续占据助手面板；父组件会先过滤已发送项，这里再只取可继续处理的建议。
const latestSuggestion = () => props.suggestions.find((item) => ['draft', 'edited', 'accepted'].includes(item.status))
const editedText = ref('')
const statusLabels: Record<string, string> = { draft: '待审阅', edited: '已编辑，待确认', accepted: '已接受', rejected: '已拒绝', confirmed: '已确认' }

function suggestionText(suggestion: AISuggestion | undefined): string {
  if (!suggestion) return ''
  return String(suggestion.edited_content?.text ?? suggestion.content.text ?? '')
}

function profileSummary(profile: CustomerProfile): string {
  const values = Object.values(profile.dimensions)
  return values.find((value) => typeof value === 'string') as string | undefined ?? '已生成客户画像，请在客户档案中查看。'
}

watch(() => props.suggestions[0]?.id, () => {
  editedText.value = suggestionText(latestSuggestion())
}, { immediate: true })

function saveEdit(): void {
  const suggestion = latestSuggestion()
  const text = editedText.value.trim()
  if (!suggestion || !text) return
  emit('edit', suggestion.id, { content: { ...suggestion.content, text } })
}

function useSuggestion(): void {
  const text = editedText.value.trim()
  const suggestion = latestSuggestion()
  if (text && suggestion) emit('useSuggestion', suggestion.id, text)
}
</script>

<template>
  <aside class="context-column">
    <section class="panel">
      <div class="panel-heading"><span>客户资料</span><small>实时摘要</small></div>
      <template v-if="customer"><dl><dt>姓名</dt><dd>{{ customer.name }}</dd><dt>电话</dt><dd>{{ customer.phone }}</dd><dt>学生 / 年级</dt><dd>{{ customer.student_name || '未填写' }} / {{ customer.grade || '未填写' }}</dd><dt>关注科目</dt><dd>{{ customer.interested_subject || '未填写' }}</dd></dl></template>
      <p v-else class="muted">请选择客户。</p>
      <div v-if="props.students.length" class="student-summary"><strong>学生资料</strong><span v-for="student in props.students" :key="student.id">{{ student.name }} · {{ student.grade || '年级未填写' }}</span></div>
    </section>
    <section class="panel timeline-panel">
      <div class="panel-heading"><span>最近动态</span><small>{{ props.timelineEvents.length }} 条</small></div>
      <p v-if="props.timelineEvents.length === 0" class="muted">暂无事件。</p>
      <article v-for="event in props.timelineEvents.slice(0, 5)" :key="event.id" class="timeline-item">
        <strong>{{ event.event_type }}</strong>
        <p>{{ event.summary }}</p>
        <small>{{ new Date(event.occurred_at).toLocaleString('zh-CN') }}</small>
      </article>
    </section>
    <section class="panel">
      <div class="panel-heading"><span>AI 助手</span><small>人工确认模式</small></div>
      <button type="button" class="primary" :disabled="busy || !customer" @click="emit('run')">{{ busy ? '生成中…' : '生成回复建议' }}</button>
      <p v-if="notice" class="notice">{{ notice }}</p><p v-if="error" class="error">{{ error }}</p>
      <div v-if="profile" class="item"><strong>客户画像：{{ statusLabels[profile.status] ?? profile.status }}</strong><p>{{ profileSummary(profile) }}</p><button v-if="profile.status === 'draft'" type="button" @click="emit('confirmProfile', profile.id)">确认画像</button></div>
      <div v-if="latestSuggestion()" class="item"><strong>回复建议：{{ statusLabels[latestSuggestion()?.status ?? ''] ?? latestSuggestion()?.status }}</strong><textarea v-model="editedText" rows="4" aria-label="AI 回复建议编辑框" /><div v-if="latestSuggestion()?.status === 'draft' || latestSuggestion()?.status === 'edited'" class="actions"><button type="button" @click="saveEdit">保存编辑</button><button type="button" @click="emit('accept', latestSuggestion()!.id)">接受建议</button><button type="button" class="danger" @click="emit('reject', latestSuggestion()!.id)">拒绝</button></div><div v-else-if="latestSuggestion()?.status === 'accepted'" class="accepted-action"><p>已接受。下一步：放入聊天框，检查后由人工发送。</p><button type="button" class="secondary" @click="useSuggestion">放入聊天框</button></div></div>
      <p v-else class="muted ai-empty">暂无待处理的回复建议。收到客户新消息后，可重新生成。</p>
    </section>
    <section class="panel hint"><strong>发送提醒</strong><p>AI 只提供建议；消息需要你最后确认后才会发送。</p></section>
  </aside>
</template>

<style scoped>
.context-column { display: grid; align-content: start; gap: 12px; }
.panel { padding: 16px; border: 1px solid #dbe3f0; border-radius: 14px; background: rgb(255 255 255 / 94%); box-shadow: 0 8px 22px rgb(30 64 175 / 5%); }
.panel-heading { display: flex; justify-content: space-between; margin-bottom: 12px; color: #1e3a8a; font-weight: 700; }
.panel-heading small, .muted { color: #64748b; font-weight: 400; }
dl { display: grid; grid-template-columns: 88px 1fr; gap: 8px; margin: 0; } dt { color: #64748b; } dd { margin: 0; font-weight: 600; }
.student-summary { display: grid; gap: 4px; margin-top: 14px; padding-top: 12px; border-top: 1px solid #e2e8f0; }.student-summary span { color: #0f766e; font-size: 13px; }
.primary, .item button { padding: 8px 10px; border: 0; border-radius: 8px; color: white; background: #2563eb; cursor: pointer; }.primary:disabled { opacity: .6; }
.item { margin-top: 12px; padding: 12px; border-radius: 10px; background: #f8fafc; }.item p { margin: 6px 0 10px; color: #475569; }.item textarea { box-sizing: border-box; width: 100%; margin: 9px 0; padding: 9px; border: 1px solid #cbd5e1; border-radius: 8px; font: inherit; }
.actions { display: flex; flex-wrap: wrap; gap: 8px; }.accepted-action { display:grid; gap:8px; }.accepted-action p { margin-bottom:0; font-size:12px; }.ai-empty { margin:12px 0 0; }.item button.danger { background: #be123c; }.item button.secondary { color: #1e40af; background: #dbeafe; }.notice { color: #166534; }.error { color: #b91c1c; }
.hint { color: #475569; border-style: dashed; background: #f8fafc; }.hint p { margin-bottom: 0; font-size: 13px; }.timeline-item { margin-top: 9px; padding: 10px; border-left: 3px solid #93c5fd; border-radius: 8px; background: #f8fbff; }.timeline-item p { margin: 4px 0; color: #475569; font-size: 13px; }.timeline-item small { color: #64748b; font-size: 11px; }
</style>
