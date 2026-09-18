<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { getAIDashboard } from '../../api/aiDashboard'
import { getBusinessDashboard, type BusinessDashboard } from '../../api/businessDashboard'
import { listPendingActions } from '../../api/pendingActions'
import { getSystemStatus } from '../../api/systemStatus'
import type { AIDashboard } from '../../types/aiDashboard'
import type { PendingAction } from '../../types/pendingAction'
import type { SystemStatus } from '../../types/systemStatus'

const loading = ref(true)
const error = ref('')
const forbidden = ref(false)
const ai = ref<AIDashboard | null>(null)
const business = ref<BusinessDashboard | null>(null)
const system = ref<SystemStatus | null>(null)
const pending = ref<PendingAction[]>([])

const stageLabels: Record<string, string> = {
  new: '新客户',
  following_up: '跟进中',
  converted: '已转化',
  lost: '已流失',
}

function dependencyLabel(name: string): string {
  return { database: '数据库', redis: 'Redis', qdrant: 'Qdrant' }[name] || name
}

function statusLabel(value: string): string {
  return { ok: '正常', error: '异常', disabled: '未启用', online: '在线', offline: '离线' }[value] || value
}

function queueDepth(): number {
  if (!system.value) return 0
  return Object.values(system.value.worker.queue_depths).reduce((total, count) => total + count, 0)
}

function loadError(reason: unknown): string {
  return reason instanceof Error ? reason.message : '管理首页数据加载失败'
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  forbidden.value = false
  const results = await Promise.allSettled([
    getAIDashboard(),
    getBusinessDashboard(),
    getSystemStatus(),
    listPendingActions(),
  ])

  const [aiResult, businessResult, systemResult, pendingResult] = results
  ai.value = aiResult.status === 'fulfilled' ? aiResult.value : null
  business.value = businessResult.status === 'fulfilled' ? businessResult.value : null
  system.value = systemResult.status === 'fulfilled' ? systemResult.value : null
  pending.value = pendingResult.status === 'fulfilled' ? pendingResult.value.items : []

  const failures = results.filter((result): result is PromiseRejectedResult => result.status === 'rejected')
  if (failures.length === results.length) {
    error.value = loadError(failures[0].reason)
  } else if (failures.length) {
    error.value = `${failures.length} 个模块暂时不可用，已显示其余可用数据。`
  }
  forbidden.value = failures.some((failure) => {
    const message = loadError(failure.reason)
    return message.includes('403') || message.includes('权限')
  })
  loading.value = false
}

onMounted(load)
</script>

<template>
  <div class="overview-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Control Center</p>
        <h1>管理总览</h1>
        <p>从一个入口查看 AI 采用、客户经营、待人工处理事项和运行依赖。</p>
      </div>
      <button type="button" :disabled="loading" @click="load">{{ loading ? '加载中…' : '刷新总览' }}</button>
    </header>

    <p v-if="loading" class="state">正在读取管理数据…</p>
    <p v-else-if="forbidden && !ai && !business && !system" class="state error">当前角色无权查看管理总览。</p>
    <template v-else>
      <p v-if="error" class="notice">{{ error }}</p>

      <section class="summary-grid">
        <RouterLink to="/admin/ai-dashboard" class="summary-card purple">
          <span>AI 采用率</span>
          <strong>{{ ai ? `${(ai.adoption_rate * 100).toFixed(1)}%` : '—' }}</strong>
          <small>{{ ai ? `${ai.feedback_total} 条人工反馈` : '暂不可用' }}</small>
        </RouterLink>
        <RouterLink to="/admin/business-dashboard" class="summary-card blue">
          <span>时间窗客户</span>
          <strong>{{ business?.customer_total ?? '—' }}</strong>
          <small>{{ business ? `${business.orders.paid_or_completed} 笔已支付/完成订单` : '暂不可用' }}</small>
        </RouterLink>
        <RouterLink to="/pending-actions" class="summary-card amber">
          <span>待人工处理</span>
          <strong>{{ pending.length }}</strong>
          <small>AI 草稿必须人工确认</small>
        </RouterLink>
        <RouterLink to="/admin/system-status" class="summary-card green">
          <span>运行状态</span>
          <strong>{{ system ? (system.ready ? '就绪' : '异常') : '—' }}</strong>
          <small>{{ system ? `Worker ${statusLabel(system.worker.status)}` : '暂不可用' }}</small>
        </RouterLink>
      </section>

      <section class="two-column">
        <article class="panel">
          <div class="panel-heading"><h2>AI 工作流</h2><RouterLink to="/admin/ai-dashboard">查看详情</RouterLink></div>
          <div v-if="ai" class="metric-list">
            <div><span>成功</span><strong>{{ ai.workflow.succeeded }}</strong></div>
            <div><span>等待人工</span><strong>{{ ai.workflow.waiting_human }}</strong></div>
            <div><span>失败</span><strong class="danger">{{ ai.workflow.failed }}</strong></div>
          </div>
          <p v-else class="muted">AI 看板暂时不可用。</p>
        </article>

        <article class="panel">
          <div class="panel-heading"><h2>客户阶段</h2><RouterLink to="/admin/business-dashboard">查看详情</RouterLink></div>
          <div v-if="business" class="stage-list">
            <RouterLink
              v-for="item in business.funnel"
              :key="item.stage"
              :to="{ name: 'customers', query: { stage: item.stage } }"
              class="stage-link"
            >
              <span>{{ stageLabels[item.stage] || item.stage }}</span><strong>{{ item.count }}</strong>
            </RouterLink>
          </div>
          <p v-else class="muted">业务看板暂时不可用。</p>
        </article>
      </section>

      <section class="panel">
        <div class="panel-heading"><h2>基础设施</h2><RouterLink to="/admin/system-status">运行状态</RouterLink></div>
        <div v-if="system" class="dependency-list">
          <div v-for="(item, name) in system.dependencies" :key="name"><span>{{ dependencyLabel(name) }}</span><strong :data-status="item.status">{{ statusLabel(item.status) }}</strong></div>
          <div><span>任务队列</span><strong :data-status="system.worker.status">{{ statusLabel(system.worker.status) }} · {{ queueDepth() }}</strong></div>
        </div>
        <p v-else class="muted">运行状态暂时不可用。</p>
      </section>

      <section class="panel">
        <div class="panel-heading"><h2>最近待处理建议</h2><RouterLink to="/pending-actions">进入人工处理</RouterLink></div>
        <div v-if="pending.length" class="pending-list">
          <RouterLink v-for="item in pending.slice(0, 5)" :key="item.id" :to="`/customers/${item.customer_id}`">
            <span>{{ item.title }}</span><small>{{ item.customer_name }} · {{ item.action_type }}</small>
          </RouterLink>
        </div>
        <p v-else class="muted">当前没有待处理建议。</p>
      </section>
    </template>
  </div>
</template>

<style scoped>
.overview-page { display: grid; gap: 20px; }
.page-header { display: flex; align-items: end; justify-content: space-between; gap: 20px; }
.page-header h1 { margin: 0; }
.page-header p:last-child, .muted, .state { color: #64748b; }
.eyebrow { margin: 0 0 6px; color: #2563eb; font-size: 12px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
button { padding: 9px 14px; border: 0; border-radius: 9px; color: #fff; background: #2563eb; cursor: pointer; }
button:disabled { cursor: wait; opacity: .6; }
.notice { margin: 0; padding: 11px 14px; border-radius: 10px; color: #92400e; background: #fffbeb; }
.error { color: #b91c1c; }
.summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.summary-card { display: block; padding: 18px; border: 1px solid #dbe5f3; border-radius: 16px; color: #1e293b; background: #fff; text-decoration: none; box-shadow: 0 8px 22px rgb(30 64 175 / 5%); }
.summary-card span, .summary-card small { display: block; color: #64748b; }.summary-card strong { display: block; margin: 9px 0 4px; font-size: 30px; }.summary-card:hover { transform: translateY(-2px); }
.summary-card.purple { border-top: 4px solid #7c3aed; }.summary-card.blue { border-top: 4px solid #2563eb; }.summary-card.amber { border-top: 4px solid #d97706; }.summary-card.green { border-top: 4px solid #16a34a; }
.two-column { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.panel { padding: 20px; border: 1px solid #dbe5f3; border-radius: 16px; background: #fff; box-shadow: 0 8px 22px rgb(30 64 175 / 5%); }
.panel-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }.panel-heading h2 { margin: 0; font-size: 18px; }.panel-heading a { color: #2563eb; font-size: 13px; font-weight: 700; text-decoration: none; }
.metric-list, .stage-list, .dependency-list { display: grid; gap: 10px; margin-top: 16px; }.metric-list { grid-template-columns: repeat(3, 1fr); }.metric-list div, .stage-link, .dependency-list div { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 12px; border-radius: 10px; background: #f8fafc; }.stage-link { color: inherit; text-decoration: none; }.stage-link:hover { background: #eff6ff; }.metric-list span, .stage-link span, .dependency-list span { color: #64748b; }.danger { color: #be123c; }
.dependency-list { grid-template-columns: repeat(4, 1fr); }.dependency-list strong { padding: 4px 8px; border-radius: 999px; color: #166534; background: #dcfce7; font-size: 12px; }.dependency-list strong[data-status="error"] { color: #991b1b; background: #fee2e2; }.dependency-list strong[data-status="offline"] { color: #92400e; background: #fef3c7; }
.pending-list { display: grid; gap: 8px; margin-top: 14px; }.pending-list a { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px; border-radius: 10px; color: #1e3a8a; background: #f8fafc; text-decoration: none; }.pending-list a:hover { background: #eff6ff; }.pending-list small { color: #64748b; }
@media (max-width: 900px) { .summary-grid { grid-template-columns: repeat(2, 1fr); }.dependency-list { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 650px) { .page-header { align-items: flex-start; flex-direction: column; }.summary-grid, .two-column, .dependency-list { grid-template-columns: 1fr; }.metric-list { grid-template-columns: repeat(3, 1fr); }.pending-list a { align-items: flex-start; flex-direction: column; } }
</style>
