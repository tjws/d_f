<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { listAIWorkflowRuns, recoverStaleWorkflowRuns } from '../../api/aiWorkflowAdmin'
import type { AIWorkflowRunAdmin, WorkflowRunStatus } from '../../types/aiWorkflowAdmin'

const items = ref<AIWorkflowRunAdmin[]>([])
const loading = ref(true)
const error = ref('')
const forbidden = ref(false)
const start = ref('')
const end = ref('')
const provider = ref('')
const status = ref<WorkflowRunStatus | ''>('')
const recovering = ref(false)
const recoveryNotice = ref('')

const statusLabels: Record<WorkflowRunStatus, string> = {
  queued: '排队中', running: '执行中', paused: '已暂停', waiting_human: '等待人工', succeeded: '成功', failed: '失败',
}
const goalLabels: Record<string, string> = { reply: '回复建议', profile: '客户画像', tag: '标签建议', schedule: '日程建议', agent_plan: 'Agent 规划' }

function isoStart(value: string): string | undefined { return value ? `${value}T00:00:00Z` : undefined }
function isoEnd(value: string): string | undefined { return value ? `${value}T23:59:59Z` : undefined }
function formatDate(value: string | null): string { return value ? new Date(value).toLocaleString('zh-CN') : '—' }

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  forbidden.value = false
  try {
    const response = await listAIWorkflowRuns({ start: isoStart(start.value), end: isoEnd(end.value), provider_name: provider.value || undefined, status: status.value || undefined })
    items.value = response.items
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '运行历史加载失败'
    forbidden.value = error.value.includes('403') || error.value.includes('权限')
  } finally {
    loading.value = false
  }
}

async function recoverStale(): Promise<void> {
  if (!window.confirm('仅标记超过 120 秒没有 Worker 心跳的 running 任务为失败，并不会自动重试。继续吗？')) return
  recovering.value = true
  recoveryNotice.value = ''
  try {
    const result = await recoverStaleWorkflowRuns({ confirm: true, stale_after_seconds: 120, limit: 50 })
    recoveryNotice.value = result.marked_failed
      ? `已标记 ${result.marked_failed} 条异常任务，可在客户页人工重试。`
      : '没有发现心跳超时的 running 任务。'
    await load()
  } catch (reason) {
    recoveryNotice.value = reason instanceof Error ? reason.message : '异常任务恢复失败'
  } finally {
    recovering.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="admin-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">AI Operations</p>
        <h1>AI 工作流运行历史</h1>
        <p>查看最近运行的状态、Provider 和失败代码；不展示模型输入输出。</p>
      </div>
      <button type="button" :disabled="loading" @click="load">{{ loading ? '加载中…' : '刷新' }}</button>
    </header>

    <section class="filters">
      <label>开始日期<input v-model="start" type="date"></label>
      <label>结束日期<input v-model="end" type="date"></label>
      <label>Provider<select v-model="provider"><option value="">全部</option><option value="bailian">bailian</option><option value="mock">mock</option></select></label>
      <label>状态<select v-model="status"><option value="">全部</option><option v-for="(label, value) in statusLabels" :key="value" :value="value">{{ label }}</option></select></label>
      <button type="button" :disabled="loading" @click="load">应用筛选</button>
    </section>

    <section class="recovery-actions">
      <div>
        <strong>Worker 恢复</strong>
        <p>将超过 120 秒没有心跳的 running 任务安全标记为失败，再由人工决定是否重试。</p>
      </div>
      <button type="button" :disabled="recovering" @click="recoverStale">{{ recovering ? '检查中…' : '检查异常任务' }}</button>
    </section>
    <p v-if="recoveryNotice" class="recovery-notice">{{ recoveryNotice }}</p>

    <p v-if="loading" class="state">正在读取运行历史…</p>
    <p v-else-if="error" class="state error">{{ forbidden ? '当前角色无权查看运行历史。' : error }}</p>
    <section v-else-if="items.length" class="table-panel">
      <table>
        <thead><tr><th>运行</th><th>目标</th><th>Provider</th><th>状态</th><th>建议数</th><th>创建时间</th><th>最近心跳</th><th>失败代码</th></tr></thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td>#{{ item.id }}<small>客户 #{{ item.customer_id }}</small></td>
            <td>{{ goalLabels[item.goal] || item.goal }}</td>
            <td><code>{{ item.provider_name }}</code></td>
            <td><span class="badge" :data-status="item.status">{{ statusLabels[item.status] }}</span></td>
            <td>{{ item.suggestion_count }}</td>
            <td>{{ formatDate(item.created_at) }}</td>
            <td>{{ formatDate(item.heartbeat_at) }}</td>
            <td>{{ item.error_code || '—' }}</td>
          </tr>
        </tbody>
      </table>
    </section>
    <section v-else class="empty"><strong>暂无运行记录</strong><p>运行 AI 工作流后，最近 7 天的记录会显示在这里。</p></section>
  </div>
    <p v-if="!loading && !error && items.some((item) => item.retryable)" class="retry-hint">
      当前列表中有失败任务可人工重试；每条任务最多 {{ items.find((item) => item.retryable)?.max_attempts ?? 3 }} 次。
    </p>
</template>

<style scoped>
.admin-page { display: grid; gap: 20px; }.page-header { display: flex; align-items: end; justify-content: space-between; gap: 20px; }.page-header h1 { margin: 0; }.page-header p:last-child, .state, .empty p { color: #64748b; }.eyebrow { margin: 0 0 6px; color: #7c3aed; font-size: 12px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
button { padding: 9px 14px; border: 0; border-radius: 8px; color: white; background: #2563eb; cursor: pointer; }button:disabled { cursor: wait; opacity: .6; }
.filters { display: flex; flex-wrap: wrap; align-items: end; gap: 10px; padding: 16px; border: 1px solid #dbe5f3; border-radius: 14px; background: white; }.filters label { display: grid; gap: 5px; color: #64748b; font-size: 12px; }.filters input, .filters select { min-width: 130px; padding: 8px; border: 1px solid #cbd5e1; border-radius: 7px; font: inherit; }
.table-panel, .empty { padding: 18px; overflow-x: auto; border: 1px solid #dbe5f3; border-radius: 16px; background: white; box-shadow: 0 8px 22px rgb(30 64 175 / 5%); }.empty { text-align: center; }.empty strong { color: #1e3a8a; font-size: 18px; }table { width: 100%; min-width: 760px; border-collapse: collapse; }th, td { padding: 11px 10px; text-align: left; border-bottom: 1px solid #e2e8f0; }th { color: #475569; font-size: 13px; }td small { display: block; margin-top: 3px; color: #94a3b8; }.badge { padding: 5px 9px; border-radius: 999px; color: #166534; background: #dcfce7; font-size: 12px; white-space: nowrap; }.badge[data-status="failed"] { color: #991b1b; background: #fee2e2; }.badge[data-status="waiting_human"] { color: #92400e; background: #fef3c7; }.badge[data-status="paused"], .badge[data-status="queued"], .badge[data-status="running"] { color: #1d4ed8; background: #dbeafe; }.error { color: #b91c1c; }
.retry-hint { margin: 0; padding: 10px 12px; border-radius: 10px; color: #92400e; background: #fef3c7; }
.recovery-actions { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 14px 16px; border: 1px solid #f1d39b; border-radius: 14px; background: #fffbeb; }.recovery-actions p { margin: 4px 0 0; color: #92400e; font-size: 13px; }.recovery-notice { margin: 0; color: #166534; }
@media (max-width: 700px) { .page-header { align-items: flex-start; flex-direction: column; } }
</style>
