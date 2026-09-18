<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getSystemStatus } from '../../api/systemStatus'
import type { DependencyState, SystemStatus } from '../../types/systemStatus'

const data = ref<SystemStatus | null>(null)
const loading = ref(true)
const error = ref('')
const forbidden = ref(false)

const labels: Record<string, string> = {
  database: 'PostgreSQL / 数据库',
  redis: 'Redis / 缓存',
  qdrant: 'Qdrant / 向量检索',
}

const stateLabels: Record<DependencyState, string> = {
  ok: '正常',
  error: '异常',
  disabled: '未启用',
}

function workerStateLabel(state: 'online' | 'offline' | 'error' | 'disabled'): string {
  return { online: '在线', offline: '离线', error: '检查失败', disabled: '未启用' }[state]
}

function queueDepth(worker: SystemStatus['worker']): string {
  return Object.values(worker.queue_depths).reduce((total, count) => total + count, 0).toString()
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  forbidden.value = false
  try {
    data.value = await getSystemStatus()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '系统状态加载失败'
    forbidden.value = error.value.includes('403') || error.value.includes('权限')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="admin-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Operations</p>
        <h1>系统运行状态</h1>
        <p>只读检查运行依赖和 AI 配置，不会调用百炼模型。</p>
      </div>
      <button type="button" :disabled="loading" @click="load">
        {{ loading ? '检查中…' : '重新检查' }}
      </button>
    </header>

    <p v-if="loading" class="muted">正在检查服务状态…</p>
    <p v-else-if="error" class="error">
      {{ forbidden ? '当前角色无权查看系统运行状态。' : error }}
    </p>
    <template v-else-if="data">
      <section class="summary" :data-ready="data.ready">
        <span class="summary-dot" aria-hidden="true"></span>
        <div>
          <strong>{{ data.ready ? '系统就绪' : '存在异常依赖' }}</strong>
          <p>检查时间：{{ new Date(data.checked_at).toLocaleString() }}</p>
        </div>
      </section>

      <section class="panel">
        <h2>基础设施</h2>
        <div class="status-grid">
          <article v-for="(item, name) in data.dependencies" :key="name" class="status-card">
            <div>
              <h3>{{ labels[name] || name }}</h3>
              <p>{{ name === 'qdrant' ? 'RAG 向量检索依赖' : '应用运行依赖' }}</p>
            </div>
            <span class="status-badge" :data-status="item.status">
              {{ stateLabels[item.status] }}
            </span>
          </article>
          <article class="status-card">
            <div>
              <h3>Dramatiq Worker / 任务执行</h3>
              <p>{{ data.worker.required ? `队列深度：${queueDepth(data.worker)}` : '当前未启用队列模式' }}</p>
            </div>
            <span class="status-badge" :data-status="data.worker.status">
              {{ workerStateLabel(data.worker.status) }}
            </span>
          </article>
        </div>
      </section>

      <section class="panel">
        <h2>数据库备份</h2>
        <div class="status-grid">
          <article class="status-card">
            <div><h3>{{ data.backup.latest_backup_name || '暂无备份' }}</h3><p>{{ data.backup.latest_backup_at ? new Date(data.backup.latest_backup_at).toLocaleString() : '请按运维计划执行备份任务' }}</p></div>
            <span class="status-badge" :data-status="data.backup.status">{{ data.backup.status === 'ok' ? '正常' : data.backup.status === 'stale' ? '过期' : data.backup.status === 'missing' ? '缺失' : '未配置' }}</span>
          </article>
          <article class="status-card"><div><h3>备份目录</h3><p>{{ data.backup.directory }}</p></div><span class="status-badge" data-status="disabled">{{ data.backup.max_age_hours }} 小时阈值</span></article>
          <article class="status-card"><div><h3>自动清理</h3><p>旧备份不会因查看状态而删除</p></div><span class="status-badge" :data-status="data.backup.automatic_prune_enabled ? 'error' : 'disabled'">{{ data.backup.automatic_prune_enabled ? '已开启' : '关闭' }}</span></article>
        </div>
      </section>

      <section class="panel">
        <h2>AI Provider 配置</h2>
        <div class="provider-grid">
          <div><span>默认 Provider</span><strong>{{ data.ai.default_provider }}</strong></div>
          <div><span>Embedding Provider</span><strong>{{ data.ai.embedding_provider }}</strong></div>
          <div><span>Embedding Model</span><strong>{{ data.ai.embedding_model }}</strong></div>
          <div><span>百炼 Key</span><strong>{{ data.ai.bailian_api_key_configured ? '已配置' : '未配置' }}</strong></div>
        </div>
        <h3>工作流 Provider</h3>
        <table>
          <thead><tr><th>能力</th><th>Provider</th></tr></thead>
          <tbody>
            <tr v-for="(provider, goal) in data.ai.workflow_providers" :key="goal">
              <td>{{ goal }}</td><td>{{ provider }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </template>
  </div>
</template>

<style scoped>
.admin-page { display: grid; gap: 20px; }
.page-header { display: flex; align-items: end; justify-content: space-between; gap: 20px; }
.page-header h1 { margin: 0; }
.page-header p:last-child, .muted { color: #64748b; }
.eyebrow { margin: 0 0 6px; color: #0f766e; font-size: 12px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
button { padding: 9px 14px; border: 0; border-radius: 8px; color: white; background: #2563eb; cursor: pointer; }
button:disabled { opacity: .6; cursor: wait; }
.summary, .panel { padding: 20px; border: 1px solid #dbe5f3; border-radius: 16px; background: white; box-shadow: 0 8px 22px rgb(30 64 175 / 5%); }
.summary { display: flex; align-items: center; gap: 12px; }
.summary[data-ready="false"] { border-color: #fecaca; background: #fff7f7; }
.summary-dot { width: 12px; height: 12px; border-radius: 50%; background: #16a34a; }
.summary[data-ready="false"] .summary-dot { background: #dc2626; }
.summary strong { font-size: 20px; }.summary p { margin: 4px 0 0; color: #64748b; }
.panel h2 { margin-top: 0; }.panel h3 { margin: 0; font-size: 16px; }
.status-grid, .provider-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.provider-grid { grid-template-columns: repeat(4, 1fr); margin-bottom: 22px; }
.status-card, .provider-grid > div { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px; border: 1px solid #e2e8f0; border-radius: 12px; }
.status-card p { margin: 5px 0 0; color: #64748b; font-size: 13px; }.provider-grid span { display: block; color: #64748b; font-size: 13px; }.provider-grid strong { display: block; margin-top: 6px; }
.status-badge { padding: 5px 9px; border-radius: 999px; color: #166534; background: #dcfce7; font-size: 12px; white-space: nowrap; }.status-badge[data-status="error"] { color: #991b1b; background: #fee2e2; }.status-badge[data-status="disabled"] { color: #475569; background: #e2e8f0; }
.status-badge[data-status="offline"] { color: #92400e; background: #fef3c7; }
table { width: 100%; border-collapse: collapse; } th, td { padding: 10px; text-align: left; border-bottom: 1px solid #e2e8f0; } th { color: #475569; font-size: 13px; }
.error { color: #b91c1c; }
@media (max-width: 900px) { .status-grid, .provider-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 620px) { .page-header { align-items: flex-start; flex-direction: column; }.status-grid, .provider-grid { grid-template-columns: 1fr; } }
</style>
