<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { getMyWork } from '../api/myWork'
import { completeSchedule } from '../api/schedules'
import type { MyWorkBucket, MyWorkItem, MyWorkResponse } from '../types/myWork'
import type { ScheduleOutcome } from '../types/schedule'

type Filter = 'all' | MyWorkBucket

const data = ref<MyWorkResponse | null>(null)
const filter = ref<Filter>('all')
const loading = ref(false)
const error = ref('')
const completionFormId = ref<string | null>(null)
const completingId = ref<string | null>(null)
const completionOutcome = ref<ScheduleOutcome>('contacted')
const completionNote = ref('')

const bucketLabels: Record<MyWorkBucket, string> = {
  review: 'AI 待审核',
  overdue: '已逾期',
  today: '今天',
  upcoming: '本周待跟进',
}

const filters: Array<{ value: Filter; label: string }> = [
  { value: 'all', label: '全部' },
  { value: 'overdue', label: '已逾期' },
  { value: 'today', label: '今天' },
  { value: 'upcoming', label: '本周待跟进' },
  { value: 'review', label: 'AI 待审核' },
]

const items = computed(() => data.value?.items ?? [])
const outcomeLabels: Record<ScheduleOutcome, string> = {
  contacted: '已联系', no_response: '未回应', appointment: '已预约',
  converted: '已成交', lost: '明确流失', other: '其他结果',
}

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString('zh-CN') : '等待人工审核'
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    data.value = await getMyWork(filter.value === 'all' ? undefined : filter.value)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '我的待办加载失败'
  } finally {
    loading.value = false
  }
}

function selectFilter(next: Filter): void {
  filter.value = next
  void load()
}

function openCompletion(item: MyWorkItem): void {
  completionFormId.value = item.id
  completionOutcome.value = 'contacted'
  completionNote.value = ''
}

function closeCompletion(): void {
  completionFormId.value = null
}

async function complete(item: MyWorkItem): Promise<void> {
  if (item.item_type !== 'schedule' || completingId.value !== null) return
  completingId.value = item.id
  error.value = ''
  try {
    await completeSchedule(item.customer_id, item.resource_id, {
      outcome: completionOutcome.value,
      completion_note: completionNote.value.trim() || null,
    })
    closeCompletion()
    await load()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '日程完成失败'
  } finally {
    completingId.value = null
  }
}

onMounted(load)
</script>

<template>
  <main class="work-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Sales Execution Center</p>
        <h1>我的待办</h1>
        <p>先处理逾期跟进，再审阅 AI 草稿；所有发送动作仍需由人工在客户工作台完成。</p>
      </div>
      <button type="button" class="refresh" :disabled="loading" @click="load">{{ loading ? '刷新中…' : '刷新' }}</button>
    </header>

    <section v-if="data" class="summary-grid">
      <button v-for="(label, key) in bucketLabels" :key="key" type="button" :class="['summary-card', key, { selected: filter === key }]" @click="selectFilter(key)">
        <span>{{ label }}</span><strong>{{ data.summary[key] }}</strong>
      </button>
    </section>

    <section class="filters">
      <button v-for="option in filters" :key="option.value" type="button" :class="{ active: filter === option.value }" @click="selectFilter(option.value)">{{ option.label }}</button>
    </section>

    <p v-if="error" class="state error">{{ error }}</p>
    <p v-else-if="loading" class="state">正在整理你的待办…</p>
    <section v-else-if="items.length" class="work-list">
      <article v-for="item in items" :key="item.id" class="work-card">
        <div class="card-topline"><span :class="['bucket', item.bucket]">{{ bucketLabels[item.bucket] }}</span><time>{{ formatDate(item.due_at || item.created_at) }}</time></div>
        <h2>{{ item.title }}</h2>
        <p class="customer">客户：{{ item.customer_name }} · {{ item.customer_stage }}</p>
        <p class="summary">{{ item.summary }}</p>
        <div class="card-actions">
          <button v-if="item.item_type === 'schedule'" type="button" class="complete" :disabled="completingId !== null" @click="openCompletion(item)">记录结果</button>
          <RouterLink :to="`/customers/${item.customer_id}`">{{ item.item_type === 'schedule' ? '查看客户' : '进入人工审核' }} →</RouterLink>
        </div>
        <form v-if="completionFormId === item.id" class="completion-form" @submit.prevent="complete(item)">
          <label>跟进结果
            <select v-model="completionOutcome"><option v-for="(label, value) in outcomeLabels" :key="value" :value="value">{{ label }}</option></select>
          </label>
          <label>备注（可选，最多 500 字）<input v-model="completionNote" maxlength="500" placeholder="例如：已约好周末试听" /></label>
          <div><button type="submit" class="complete" :disabled="completingId !== null">{{ completingId === item.id ? '保存中…' : '保存结果并完成' }}</button><button type="button" class="cancel" @click="closeCompletion">取消</button></div>
        </form>
      </article>
    </section>
    <section v-else class="empty-state"><strong>当前没有 {{ filter === 'all' ? '' : bucketLabels[filter] }} 待办</strong><p>创建并确认日程后会显示在这里；AI 草稿则会进入人工审核队列。</p><RouterLink to="/customers">前往客户工作台</RouterLink></section>
  </main>
</template>

<style scoped>
.work-page { min-height: 100vh; padding: 40px 6vw 72px; color: #1e293b; background: linear-gradient(180deg, #eff6ff 0, #f8fafc 340px); }.page-header { display: flex; align-items: end; justify-content: space-between; gap: 24px; max-width: 1120px; margin: 0 auto 24px; }.eyebrow { margin: 0 0 8px; color: #2563eb; font-size: 12px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }.page-header h1 { margin: 0; font-size: clamp(30px, 5vw, 44px); }.page-header p:last-child { color: #64748b; line-height: 1.7; }.refresh { padding: 10px 15px; border: 0; border-radius: 10px; color: white; background: #1d4ed8; cursor: pointer; }.refresh:disabled { opacity: .65; cursor: wait; }
.summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; max-width: 1120px; margin: 0 auto 18px; }.summary-card { display: grid; gap: 7px; padding: 16px; border: 1px solid #dbe4f0; border-radius: 14px; text-align: left; background: white; cursor: pointer; }.summary-card span { color: #64748b; font-size: 13px; }.summary-card strong { color: #1e3a8a; font-size: 28px; }.summary-card.selected, .summary-card:hover { border-color: #60a5fa; background: #eff6ff; }.summary-card.overdue strong { color: #b91c1c; }.summary-card.today strong { color: #c2410c; }
.filters { display: flex; flex-wrap: wrap; gap: 8px; max-width: 1120px; margin: 0 auto 18px; }.filters button { padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 999px; color: #475569; background: white; cursor: pointer; }.filters button.active { border-color: #2563eb; color: white; background: #2563eb; }.work-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; max-width: 1120px; margin: 0 auto; }.work-card { display: grid; gap: 10px; padding: 20px; border: 1px solid #dbe4f0; border-radius: 16px; background: rgb(255 255 255 / 94%); box-shadow: 0 8px 22px rgb(30 64 175 / 6%); }.card-topline, .card-actions { display: flex; align-items: center; justify-content: space-between; gap: 10px; }.card-topline time { color: #94a3b8; font-size: 12px; }.bucket { padding: 4px 8px; border-radius: 999px; font-size: 12px; font-weight: 700; }.bucket.overdue { color: #991b1b; background: #fee2e2; }.bucket.today { color: #9a3412; background: #ffedd5; }.bucket.upcoming { color: #1d4ed8; background: #dbeafe; }.bucket.review { color: #6d28d9; background: #ede9fe; }.work-card h2, .work-card p { margin: 0; }.work-card h2 { font-size: 19px; }.customer { color: #475569; font-size: 14px; }.summary { color: #64748b; line-height: 1.6; }.card-actions { margin-top: 4px; }.card-actions a { color: #1d4ed8; font-weight: 700; text-decoration: none; }.complete { padding: 8px 10px; border: 0; border-radius: 8px; color: white; background: #15803d; cursor: pointer; }.complete:disabled { opacity: .6; cursor: wait; }.state, .empty-state { max-width: 1120px; margin: 24px auto; color: #64748b; }.error { color: #b91c1c; }.empty-state { padding: 38px; border: 1px dashed #bfdbfe; border-radius: 16px; text-align: center; background: rgb(255 255 255 / 72%); }.empty-state strong { display: block; color: #1e3a8a; font-size: 18px; }.empty-state a { color: #1d4ed8; font-weight: 700; text-decoration: none; }
@media (max-width: 760px) { .page-header { align-items: start; flex-direction: column; }.summary-grid { grid-template-columns: repeat(2, 1fr); }.work-list { grid-template-columns: 1fr; } }
.cancel { margin-left: 8px; color: #475569; background: #e2e8f0; }.completion-form { display: grid; gap: 9px; padding: 12px; border: 1px solid #bbf7d0; border-radius: 10px; background: #f0fdf4; }.completion-form label { display: grid; gap: 4px; color: #166534; font-size: 13px; font-weight: 700; }.completion-form input, .completion-form select { box-sizing: border-box; width: 100%; padding: 8px; border: 1px solid #86efac; border-radius: 7px; font: inherit; }
</style>
