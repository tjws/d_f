<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { createChurnIntervention, getChurnScoringBatch, listChurnScoringBatches } from '../api/churnRisks'
import type { ChurnRiskPrediction, ChurnScoringBatch } from '../types/churnRisk'

const batches = ref<ChurnScoringBatch[]>([])
const risks = ref<ChurnRiskPrediction[]>([])
const loading = ref(true)
const error = ref('')
const selectedRisk = ref<ChurnRiskPrediction | null>(null)
const actionBusy = ref(false)
const actionMessage = ref('')
const dueAt = ref(defaultDueAt())

const highRisks = computed(() => risks.value.filter((item) => item.risk_level === 'high'))
const mediumRisks = computed(() => risks.value.filter((item) => item.risk_level === 'medium'))
const actionableRisks = computed(() => risks.value.filter((item) => !item.intervention || !['completed', 'cancelled'].includes(item.intervention.status)))

function defaultDueAt(): string {
  const value = new Date(Date.now() + 24 * 60 * 60 * 1000)
  value.setMinutes(value.getMinutes() - value.getTimezoneOffset())
  return value.toISOString().slice(0, 16)
}

function riskLabel(level: string): string {
  return level === 'high' ? '优先跟进' : '建议关注'
}

function reason(item: ChurnRiskPrediction): string {
  // 当前模型只提供排序和等级，尚未实现可解释特征归因，不能编造具体原因。
  return item.risk_level === 'high'
    ? '系统将该客户排在本次名单前列，建议优先进行人工沟通。'
    : '系统识别到需要关注，建议结合近期沟通情况安排人工跟进。'
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    const response = await listChurnScoringBatches({ status: 'completed', limit: 20 })
    batches.value = response.items
    const latest = response.items[0]
    if (!latest) {
      risks.value = []
      return
    }
    const detail = await getChurnScoringBatch(latest.id, { page_size: 200 })
    // 仅展示已映射到本人可访问客户的高、中风险，低风险和未映射数据留在管理后台。
    risks.value = detail.items.filter(
      (item) => item.mapping_status === 'mapped' && item.customer_id !== null && ['high', 'medium'].includes(item.risk_level),
    )
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '风险工作台加载失败'
  } finally {
    loading.value = false
  }
}

function chooseRisk(item: ChurnRiskPrediction): void {
  selectedRisk.value = item
  actionMessage.value = ''
  dueAt.value = defaultDueAt()
}

async function createFollowUp(): Promise<void> {
  if (!selectedRisk.value || !dueAt.value) return
  actionBusy.value = true
  actionMessage.value = ''
  try {
    await createChurnIntervention(selectedRisk.value.id, {
      action_type: 'mock_wecom',
      due_at: new Date(dueAt.value).toISOString(),
    })
    actionMessage.value = '已创建人工跟进，并同步到客户日程和时间线。'
    await load()
  } catch (reason) {
    actionMessage.value = reason instanceof Error ? reason.message : '创建跟进失败'
  } finally {
    actionBusy.value = false
  }
}

onMounted(() => { void load() })
</script>

<template>
  <main class="risk-workbench">
    <header class="hero">
      <div><p class="eyebrow">PRIORITY FOLLOW-UP</p><h1>我的优先跟进</h1><p>风险排序只帮助你安排先后；沟通内容、跟进方式和发送动作始终由你决定。</p></div>
      <button type="button" :disabled="loading" @click="load">{{ loading ? '正在刷新…' : '刷新名单' }}</button>
    </header>

    <p v-if="error" class="state error">{{ error }}</p>
    <template v-else-if="loading"><section class="empty"><strong>正在整理你的待跟进客户…</strong></section></template>
    <template v-else-if="!batches.length"><section class="empty"><strong>暂时没有可处理的风险客户</strong><p>风险模型完成评分后，系统会把属于你的高优先级客户放到这里。</p></section></template>
    <template v-else>
      <section class="summary">
        <article class="high"><span>优先跟进</span><strong>{{ highRisks.length }}</strong><small>建议优先联系</small></article>
        <article class="medium"><span>建议关注</span><strong>{{ mediumRisks.length }}</strong><small>可结合日常节奏安排</small></article>
        <article><span>尚待处理</span><strong>{{ actionableRisks.length }}</strong><small>未完成人工干预</small></article>
      </section>

      <section class="list-panel">
        <div class="section-head"><div><p class="eyebrow">ACTION QUEUE</p><h2>先处理这些客户</h2></div><small>仅展示你有权限查看的客户</small></div>
        <p v-if="!risks.length" class="empty">本次评分中没有属于你的高、中风险客户。</p>
        <article v-for="item in risks" :key="item.id" class="risk-card" :class="item.risk_level">
          <div class="priority"><span>{{ riskLabel(item.risk_level) }}</span><small>本次优先级 #{{ item.risk_rank }}</small></div>
          <div class="risk-main"><strong>{{ item.customer_name || '待映射客户' }}</strong><p>{{ reason(item) }}</p><small v-if="item.intervention">当前跟进：{{ item.intervention.status }}</small><small v-else>尚未创建跟进</small></div>
          <div class="actions"><RouterLink :to="{ name: 'customer-detail', params: { customerId: item.customer_id } }">进入客户沟通</RouterLink><button v-if="!item.intervention" type="button" @click="chooseRisk(item)">创建跟进</button></div>
        </article>
      </section>

      <section v-if="selectedRisk" class="follow-up-panel">
        <div class="section-head"><div><p class="eyebrow">HUMAN FOLLOW-UP</p><h2>安排 {{ selectedRisk.customer_name }} 的人工跟进</h2></div><button type="button" class="secondary" @click="selectedRisk = null">关闭</button></div>
        <p>系统只提示优先级。创建后会生成正式日程并记录到客户时间线，不会自动发消息。</p>
        <div class="follow-up-form"><label>计划联系时间<input v-model="dueAt" type="datetime-local"></label><button type="button" :disabled="actionBusy || !dueAt" @click="createFollowUp">{{ actionBusy ? '正在创建…' : '创建人工跟进' }}</button></div>
        <p v-if="actionMessage" class="action-message">{{ actionMessage }}</p>
      </section>
    </template>
  </main>
</template>

<style scoped>
.risk-workbench { display:grid; gap:20px; max-width:1180px; margin:0 auto; padding:34px clamp(18px,4vw,60px) 56px; }.hero { display:flex; align-items:center; justify-content:space-between; gap:20px; padding:30px; border-radius:22px; color:#fff; background:linear-gradient(120deg,#183c9f,#5b21b6); box-shadow:0 18px 42px rgb(49 46 129 / 20%); }.hero h1,.section-head h2 { margin:0; }.hero p:last-child { max-width:680px; margin:9px 0 0; color:#dbeafe; line-height:1.6; }.eyebrow { margin:0 0 7px; color:#8b5cf6; font-size:11px; font-weight:800; letter-spacing:.12em; }.hero .eyebrow { color:#bfdbfe; }.hero button,.actions button,.follow-up-form button { padding:10px 14px; border:0; border-radius:9px; color:#1e3a8a; background:#fff; cursor:pointer; font:inherit; font-weight:800; white-space:nowrap; }.hero button:disabled,.follow-up-form button:disabled { opacity:.55; cursor:wait; }.summary { display:grid; grid-template-columns:repeat(3,1fr); gap:13px; }.summary article,.list-panel,.follow-up-panel,.empty { padding:20px; border:1px solid #dbe5f3; border-radius:16px; background:#fff; box-shadow:0 8px 22px rgb(30 64 175 / 5%); }.summary article { display:grid; gap:6px; }.summary span,.summary small,.section-head small,.risk-main small { color:#64748b; }.summary strong { font-size:30px; color:#1e3a8a; }.summary .high strong { color:#be123c; }.summary .medium strong { color:#b45309; }.section-head { display:flex; align-items:flex-end; justify-content:space-between; gap:12px; margin-bottom:14px; }.risk-card { display:grid; grid-template-columns:132px minmax(0,1fr) auto; gap:16px; align-items:center; padding:16px 0; border-top:1px solid #e2e8f0; }.risk-card.high { border-left:4px solid #fb7185; padding-left:13px; }.risk-card.medium { border-left:4px solid #fbbf24; padding-left:13px; }.priority { display:grid; gap:4px; }.priority span { color:#9f1239; font-weight:800; }.medium .priority span { color:#92400e; }.priority small { color:#64748b; font-size:12px; }.risk-main { display:grid; gap:5px; }.risk-main strong { color:#172554; font-size:17px; }.risk-main p,.follow-up-panel p { margin:0; color:#475569; line-height:1.55; }.actions { display:flex; flex-wrap:wrap; gap:8px; }.actions a,.actions button { padding:8px 10px; border-radius:8px; color:#1d4ed8; background:#eaf1ff; text-decoration:none; }.actions button { color:#fff; background:#2563eb; }.follow-up-panel { display:grid; gap:14px; }.follow-up-form { display:flex; flex-wrap:wrap; align-items:end; gap:12px; }.follow-up-form label { display:grid; gap:5px; color:#64748b; font-size:12px; }.follow-up-form input { min-width:240px; padding:9px; border:1px solid #cbd5e1; border-radius:8px; font:inherit; }.follow-up-form button { color:#fff; background:#0f766e; }.secondary { padding:8px 10px; border:1px solid #cbd5e1; border-radius:8px; color:#475569; background:#fff; cursor:pointer; }.action-message { color:#166534 !important; font-weight:700; }.empty { color:#64748b; text-align:center; }.empty strong { color:#1e3a8a; font-size:18px; }.state.error { color:#b91c1c; }@media (max-width:760px) { .hero,.section-head { align-items:flex-start; flex-direction:column; }.summary { grid-template-columns:1fr; }.risk-card { grid-template-columns:1fr; }.actions { justify-content:flex-start; } }
</style>
