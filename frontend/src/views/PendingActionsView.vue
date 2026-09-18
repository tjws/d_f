<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { decidePendingAction, listPendingActions } from '../api/pendingActions'
import type { PendingAction, PendingActionType } from '../types/pendingAction'

type Filter = 'all' | PendingActionType

const items = ref<PendingAction[]>([])
const loading = ref(false)
const error = ref('')
const filter = ref<Filter>('all')
const actingId = ref<string | null>(null)

const labels: Record<PendingActionType, string> = {
  profile: '客户画像',
  reply: '回复建议',
  tag: '标签建议',
  schedule: '日程建议',
}

const filterOptions: Array<{ value: Filter; label: string }> = [
  { value: 'all', label: '全部待处理' },
  ...Object.entries(labels).map(([value, label]) => ({ value: value as PendingActionType, label })),
]

const visibleTotal = computed(() => items.value.length)

function formatDate(value: string): string {
  return new Date(value).toLocaleString('zh-CN')
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const response = await listPendingActions(filter.value === 'all' ? undefined : filter.value)
    items.value = response.items
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '待处理建议加载失败'
  } finally {
    loading.value = false
  }
}

function selectFilter(next: Filter): void {
  filter.value = next
  void load()
}

async function decide(item: PendingAction, action: 'accepted' | 'rejected'): Promise<void> {
  if (actingId.value !== null) return
  actingId.value = item.id
  error.value = ''
  try {
    await decidePendingAction(item.action_type, item.resource_id, action)
    await load()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '人工处理失败'
  } finally {
    actingId.value = null
  }
}

onMounted(load)
</script>

<template>
  <main class="pending-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Human Review Queue</p>
        <h1>待处理 AI 建议</h1>
        <p>所有内容均由 AI 生成草稿，必须进入客户工作台后由人工确认、编辑或拒绝。</p>
      </div>
      <button type="button" class="refresh" :disabled="loading" @click="load">{{ loading ? '加载中…' : '刷新列表' }}</button>
    </header>

    <section class="filters" aria-label="待处理建议类型筛选">
      <button v-for="option in filterOptions" :key="option.value" type="button" :class="{ active: filter === option.value }" @click="selectFilter(option.value)">
        {{ option.label }}
      </button>
    </section>

    <p v-if="error" class="state error">{{ error }}</p>
    <p v-else-if="loading" class="state">正在读取你的待处理建议…</p>
    <section v-else-if="visibleTotal" class="action-list">
      <article v-for="item in items" :key="item.id" class="action-card">
        <div class="card-topline">
          <span class="type-badge" :class="item.action_type">{{ labels[item.action_type] }}</span>
          <time>{{ formatDate(item.created_at) }}</time>
        </div>
        <h2>{{ item.title }}</h2>
        <p class="customer">客户：{{ item.customer_name }} · {{ item.customer_stage }}</p>
        <p class="summary">{{ item.summary }}</p>
        <div v-if="item.status !== 'accepted'" class="card-actions">
          <button type="button" class="accept" :disabled="actingId !== null" @click="decide(item, 'accepted')">接受</button>
          <button type="button" class="reject" :disabled="actingId !== null" @click="decide(item, 'rejected')">拒绝</button>
        </div>
        <p v-else-if="item.action_type === 'reply'" class="accepted-hint">已接受，下一步请进入客户工作台，把建议放入聊天框并人工发送。</p>
        <RouterLink :to="`/customers/${item.customer_id}`" class="review-link">进入客户工作台处理 →</RouterLink>
      </article>
    </section>
    <section v-else class="empty-state">
      <strong>当前没有待处理建议</strong>
      <p>当 Agent 或 AI 工作流生成画像、回复、标签或日程草稿后，它们会出现在这里。</p>
      <RouterLink to="/customers">前往客户工作台</RouterLink>
    </section>
  </main>
</template>

<style scoped>
.pending-page { min-height: 100vh; padding: 40px 6vw 72px; color: #1e293b; background: linear-gradient(180deg, #eff6ff 0, #f8fafc 340px); }
.page-header { display: flex; justify-content: space-between; align-items: end; gap: 24px; max-width: 1120px; margin: 0 auto 26px; }.eyebrow { margin: 0 0 8px; color: #2563eb; font-size: 12px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }.page-header h1 { margin: 0; font-size: clamp(30px, 5vw, 44px); }.page-header p:last-child { max-width: 660px; color: #64748b; line-height: 1.7; }.refresh { padding: 10px 15px; border: 0; border-radius: 10px; color: white; background: #1d4ed8; cursor: pointer; white-space: nowrap; }.refresh:disabled { cursor: wait; opacity: .7; }
.filters { display: flex; flex-wrap: wrap; gap: 8px; max-width: 1120px; margin: 0 auto 18px; }.filters button { padding: 8px 12px; border: 1px solid #cbd5e1; border-radius: 999px; color: #475569; background: white; cursor: pointer; }.filters button.active { border-color: #2563eb; color: white; background: #2563eb; }
.action-list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; max-width: 1120px; margin: 0 auto; }.action-card { display: grid; gap: 10px; padding: 20px; border: 1px solid #dbe4f0; border-radius: 16px; background: rgb(255 255 255 / 94%); box-shadow: 0 8px 22px rgb(30 64 175 / 6%); }.card-topline { display: flex; justify-content: space-between; align-items: center; gap: 10px; }.card-topline time { color: #94a3b8; font-size: 12px; }.type-badge { padding: 4px 8px; border-radius: 999px; font-size: 12px; font-weight: 700; }.type-badge.profile { color: #6d28d9; background: #ede9fe; }.type-badge.reply { color: #0369a1; background: #e0f2fe; }.type-badge.tag { color: #b45309; background: #fef3c7; }.type-badge.schedule { color: #166534; background: #dcfce7; }.action-card h2 { margin: 0; font-size: 19px; }.customer, .summary { margin: 0; line-height: 1.6; }.customer { color: #475569; font-size: 14px; }.summary { color: #64748b; }.review-link { margin-top: 4px; color: #1d4ed8; font-weight: 700; text-decoration: none; }.review-link:hover { text-decoration: underline; }.state, .empty-state { max-width: 1120px; margin: 24px auto; color: #64748b; }.error { color: #b91c1c; }.empty-state { padding: 38px; border: 1px dashed #bfdbfe; border-radius: 16px; text-align: center; background: rgb(255 255 255 / 72%); }.empty-state strong { display: block; color: #1e3a8a; font-size: 18px; }.empty-state a { color: #1d4ed8; font-weight: 700; text-decoration: none; }
@media (max-width: 720px) { .page-header { align-items: start; flex-direction: column; }.action-list { grid-template-columns: 1fr; } }
.card-actions { display: flex; gap: 8px; margin-top: 4px; }
.card-actions button { padding: 7px 10px; border: 0; border-radius: 8px; color: white; cursor: pointer; }
.card-actions button:disabled { cursor: wait; opacity: .6; }
.card-actions .accept { background: #15803d; }
.card-actions .reject { background: #be123c; }
.accepted-hint { margin: 0; padding: 9px 11px; border-radius: 9px; color: #075985; background: #e0f2fe; font-size: 13px; line-height: 1.5; }
</style>
