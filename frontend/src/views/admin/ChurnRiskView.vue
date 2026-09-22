<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  approveChurnModel,
  createChurnIntervention,
  createExternalStudentMapping,
  getChurnScoringBatch,
  listChurnModels,
  listChurnScoringBatches,
  registerChurnModel,
  updateChurnIntervention,
} from '../../api/churnRisks'
import { useAuth } from '../../composables/useAuth'
import type {
  ChurnBatchStatus,
  ChurnRiskBatchDetail,
  ChurnRiskLevel,
  ChurnScoringBatch,
  ChurnModelVersion,
  ChurnRiskPrediction,
  ChurnInterventionOutcome,
} from '../../types/churnRisk'

const { currentRole } = useAuth()

const batches = ref<ChurnScoringBatch[]>([])
const batchTotal = ref(0)
const selectedBatchId = ref<number | null>(null)
const detail = ref<ChurnRiskBatchDetail | null>(null)
const loadingBatches = ref(true)
const loadingDetail = ref(false)
const error = ref('')
const forbidden = ref(false)

const start = ref('')
const end = ref('')
const batchStatus = ref<ChurnBatchStatus | ''>('')
const riskLevel = ref<ChurnRiskLevel | ''>('')
const keyword = ref('')
const page = ref(1)
const pageSize = 50
const selectedRisk = ref<ChurnRiskPrediction | null>(null)
const mappingStudentId = ref('')
const actionType = ref('phone_call')
const interventionDueAt = ref('')
const interventionNote = ref('')
const interventionOutcome = ref<ChurnInterventionOutcome>('unknown')
const actionBusy = ref(false)
const actionMessage = ref('')
const models = ref<ChurnModelVersion[]>([])
const modelVersion = ref('')
const artifactFilename = ref('churn_logistic_baseline.joblib')
const reportFilename = ref('churn_logistic_baseline_report.json')

const pageCount = computed(() => Math.max(1, Math.ceil((detail.value?.total ?? 0) / pageSize)))
const riskLabels: Record<ChurnRiskLevel, string> = { high: '高风险', medium: '中风险', low: '低风险' }
const batchStatusLabels: Record<ChurnBatchStatus, string> = { running: '评分中', completed: '已完成', failed: '失败' }

function isoStart(value: string): string | undefined { return value ? `${value}T00:00:00Z` : undefined }
function isoEnd(value: string): string | undefined { return value ? `${value}T23:59:59Z` : undefined }
function formatDate(value: string | null): string { return value ? new Date(value).toLocaleString('zh-CN') : '—' }
function formatScore(value: number): string { return `${(value * 100).toFixed(1)}` }
function defaultDueAt(): string {
  const value = new Date(Date.now() + 24 * 60 * 60 * 1000)
  return new Date(value.getTime() - value.getTimezoneOffset() * 60_000).toISOString().slice(0, 16)
}

async function loadBatches(): Promise<void> {
  loadingBatches.value = true
  error.value = ''
  forbidden.value = false
  try {
    const response = await listChurnScoringBatches({
      start: isoStart(start.value),
      end: isoEnd(end.value),
      status: batchStatus.value || undefined,
      limit: 100,
    })
    batches.value = response.items
    batchTotal.value = response.total
    if (!response.items.length) {
      selectedBatchId.value = null
      detail.value = null
      return
    }
    if (!response.items.some((item) => item.id === selectedBatchId.value)) {
      selectedBatchId.value = response.items[0].id
    }
    await loadDetail()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '流失风险批次加载失败'
    forbidden.value = error.value.includes('403') || error.value.includes('权限')
  } finally {
    loadingBatches.value = false
  }
}

async function loadDetail(): Promise<void> {
  if (selectedBatchId.value === null) return
  loadingDetail.value = true
  error.value = ''
  try {
    detail.value = await getChurnScoringBatch(selectedBatchId.value, {
      risk_level: riskLevel.value || undefined,
      keyword: keyword.value.trim() || undefined,
      page: page.value,
      page_size: pageSize,
    })
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '风险名单加载失败'
  } finally {
    loadingDetail.value = false
  }
}

async function selectBatch(batchId: number): Promise<void> {
  selectedBatchId.value = batchId
  riskLevel.value = ''
  keyword.value = ''
  page.value = 1
  await loadDetail()
}

async function applyRiskFilters(): Promise<void> {
  page.value = 1
  await loadDetail()
}

async function changePage(nextPage: number): Promise<void> {
  page.value = Math.max(1, Math.min(nextPage, pageCount.value))
  await loadDetail()
}

function chooseRisk(item: ChurnRiskPrediction): void {
  selectedRisk.value = item
  mappingStudentId.value = item.student_id ? String(item.student_id) : ''
  interventionDueAt.value = defaultDueAt()
  actionMessage.value = ''
}

async function saveMapping(): Promise<void> {
  if (!selectedRisk.value || !mappingStudentId.value) return
  actionBusy.value = true
  actionMessage.value = ''
  try {
    const sourceSystem = detail.value?.batch.source_system || 'csv'
    const result = await createExternalStudentMapping({
      source_system: sourceSystem,
      external_student_id: selectedRisk.value.student_external_id,
      student_id: Number(mappingStudentId.value),
    })
    actionMessage.value = `映射成功，并关联 ${result.rebound_prediction_count} 条历史风险记录。`
    await loadDetail()
    selectedRisk.value = detail.value?.items.find((item) => item.id === selectedRisk.value?.id) ?? null
  } catch (reason) {
    actionMessage.value = reason instanceof Error ? reason.message : '映射失败'
  } finally {
    actionBusy.value = false
  }
}

async function saveIntervention(): Promise<void> {
  if (!selectedRisk.value || !interventionDueAt.value) return
  actionBusy.value = true
  actionMessage.value = ''
  try {
    await createChurnIntervention(selectedRisk.value.id, {
      action_type: actionType.value,
      due_at: new Date(interventionDueAt.value).toISOString(),
      note: interventionNote.value.trim() || undefined,
    })
    actionMessage.value = '人工跟进已创建，并同步进入日程和客户时间线。'
    await loadDetail()
    selectedRisk.value = detail.value?.items.find((item) => item.id === selectedRisk.value?.id) ?? null
  } catch (reason) {
    actionMessage.value = reason instanceof Error ? reason.message : '创建干预失败'
  } finally {
    actionBusy.value = false
  }
}

async function finishIntervention(): Promise<void> {
  const intervention = selectedRisk.value?.intervention
  if (!intervention) return
  actionBusy.value = true
  try {
    await updateChurnIntervention(intervention.id, {
      status: 'completed',
      outcome: interventionOutcome.value,
      note: interventionNote.value.trim() || undefined,
    })
    actionMessage.value = '干预结果已记录，日程和时间线已同步更新。'
    await loadDetail()
    selectedRisk.value = detail.value?.items.find((item) => item.id === selectedRisk.value?.id) ?? null
  } catch (reason) {
    actionMessage.value = reason instanceof Error ? reason.message : '完成干预失败'
  } finally {
    actionBusy.value = false
  }
}

async function loadModels(): Promise<void> {
  if (currentRole.value === 'sales') return
  try { models.value = await listChurnModels() } catch { models.value = [] }
}

async function saveModel(): Promise<void> {
  actionBusy.value = true
  try {
    await registerChurnModel({
      artifact_filename: artifactFilename.value,
      report_filename: reportFilename.value || undefined,
      version: modelVersion.value,
    })
    actionMessage.value = '候选模型已登记，审批后才能用于定时评分。'
    await loadModels()
  } catch (reason) {
    actionMessage.value = reason instanceof Error ? reason.message : '模型登记失败'
  } finally { actionBusy.value = false }
}

async function approveModel(modelId: number): Promise<void> {
  actionBusy.value = true
  try {
    await approveChurnModel(modelId)
    actionMessage.value = '模型已审批；之前的已审批模型已自动退役。'
    await loadModels()
  } catch (reason) {
    actionMessage.value = reason instanceof Error ? reason.message : '模型审批失败'
  } finally { actionBusy.value = false }
}

onMounted(async () => { await Promise.all([loadBatches(), loadModels()]) })
</script>

<template>
  <div class="admin-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Churn Risk</p>
        <h1>客户流失风险</h1>
        <p>查看离线模型的评分批次与风险排序。分值仅用于人工确定跟进优先级。</p>
      </div>
      <button type="button" :disabled="loadingBatches" @click="loadBatches">
        {{ loadingBatches ? '加载中…' : '刷新' }}
      </button>
    </header>

    <section class="filters">
      <label>开始日期<input v-model="start" type="date"></label>
      <label>结束日期<input v-model="end" type="date"></label>
      <label>批次状态
        <select v-model="batchStatus">
          <option value="">全部</option>
          <option value="completed">已完成</option>
          <option value="running">评分中</option>
          <option value="failed">失败</option>
        </select>
      </label>
      <button type="button" :disabled="loadingBatches" @click="loadBatches">应用筛选</button>
    </section>

    <p v-if="error && forbidden" class="state error">当前角色无权查看客户流失风险。</p>
    <p v-else-if="error" class="state error">{{ error }}</p>
    <p v-if="loadingBatches" class="state">正在读取评分批次…</p>

    <template v-else-if="!forbidden">
      <section v-if="batches.length" class="batch-panel">
        <div class="section-heading">
          <div><p class="eyebrow">Scoring Batches</p><h2>评分批次</h2></div>
          <span>{{ batchTotal }} 个批次</span>
        </div>
        <div class="batch-list">
          <button
            v-for="batch in batches"
            :key="batch.id"
            type="button"
            class="batch-card"
            :class="{ active: selectedBatchId === batch.id }"
            @click="selectBatch(batch.id)"
          >
            <span><strong>批次 #{{ batch.id }}</strong><small>{{ batch.source_filename }}</small></span>
            <span><b :data-status="batch.status">{{ batchStatusLabels[batch.status] }}</b><small>{{ formatDate(batch.created_at) }}</small></span>
          </button>
        </div>
      </section>

      <section v-if="detail" class="summary-grid">
        <article><span>总评分数</span><strong>{{ detail.batch.scored_count }}</strong></article>
        <article class="high"><span>高风险</span><strong>{{ detail.batch.high_count }}</strong></article>
        <article class="medium"><span>中风险</span><strong>{{ detail.batch.medium_count }}</strong></article>
        <article class="low"><span>低风险</span><strong>{{ detail.batch.low_count }}</strong></article>
      </section>

      <section v-if="detail" class="trace-panel">
        <div><span>模型</span><strong>{{ detail.batch.model_name }}</strong></div>
        <div><span>数据契约</span><code>{{ detail.batch.model_schema_version }}</code></div>
        <div><span>高风险阈值</span><strong>{{ formatScore(detail.batch.decision_threshold) }} 分</strong></div>
        <div><span>中风险阈值</span><strong>{{ formatScore(detail.batch.medium_threshold) }} 分</strong></div>
        <div><span>数据指纹</span><code :title="detail.batch.source_sha256">{{ detail.batch.source_sha256.slice(0, 12) }}…</code></div>
        <div><span>分布漂移</span><strong :class="{ danger: detail.batch.drift_status === 'alert' }">{{ detail.batch.drift_status }}</strong></div>
      </section>

      <section v-if="detail" class="risk-panel">
        <div class="section-heading">
          <div><p class="eyebrow">Priority List</p><h2>风险排序</h2></div>
          <span>筛选后 {{ detail.total }} 条</span>
        </div>
        <div class="risk-filters">
          <label>风险等级
            <select v-model="riskLevel">
              <option value="">全部</option>
              <option value="high">高风险</option>
              <option value="medium">中风险</option>
              <option value="low">低风险</option>
            </select>
          </label>
          <label>学生外部编号<input v-model="keyword" type="search" placeholder="例如 7024"></label>
          <button type="button" :disabled="loadingDetail" @click="applyRiskFilters">查询</button>
        </div>

        <p v-if="loadingDetail" class="state">正在读取风险名单…</p>
        <div v-else-if="detail.items.length" class="table-wrap">
          <table>
            <thead><tr><th>排名</th><th>学生 / 客户</th><th>风险等级</th><th>风险分值</th><th>跟进状态</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="item in detail.items" :key="item.id">
                <td><strong>#{{ item.risk_rank }}</strong></td>
                <td>
                  <code>{{ item.student_external_id }}</code>
                  <RouterLink v-if="item.customer_id" :to="`/customers/${item.customer_id}`">{{ item.customer_name }}</RouterLink>
                  <small v-else>尚未映射到系统学生</small>
                </td>
                <td><span class="risk-badge" :data-level="item.risk_level">{{ riskLabels[item.risk_level] }}</span></td>
                <td>{{ formatScore(item.risk_score) }}<small>/ 100，仅用于排序</small></td>
                <td>{{ item.intervention?.status || '未跟进' }}<small>前 {{ ((1 - item.risk_percentile) * 100).toFixed(1) }}%</small></td>
                <td><button type="button" class="secondary" @click="chooseRisk(item)">处理</button></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="empty">当前筛选条件下没有风险记录。</div>
        <footer v-if="detail.total > pageSize" class="pagination">
          <button type="button" :disabled="page <= 1 || loadingDetail" @click="changePage(page - 1)">上一页</button>
          <span>第 {{ page }} / {{ pageCount }} 页</span>
          <button type="button" :disabled="page >= pageCount || loadingDetail" @click="changePage(page + 1)">下一页</button>
        </footer>
      </section>

      <section v-if="selectedRisk" class="action-panel">
        <div class="section-heading">
          <div><p class="eyebrow">Human Action</p><h2>人工干预 · #{{ selectedRisk.risk_rank }}</h2></div>
          <button type="button" class="secondary" @click="selectedRisk = null">关闭</button>
        </div>
        <p class="hint">模型只负责排序；映射、创建任务、填写结果都由人工确认。</p>
        <div v-if="selectedRisk.mapping_status === 'unmapped'" class="form-row">
          <label>系统学生 ID<input v-model="mappingStudentId" type="number" min="1" placeholder="在客户详情的学生资料中查看"></label>
          <button type="button" :disabled="actionBusy || !mappingStudentId" @click="saveMapping">建立映射</button>
        </div>
        <div v-else-if="!selectedRisk.intervention" class="form-grid">
          <label>人工跟进方式<select v-model="actionType"><option value="phone_call">电话</option><option value="mock_wecom">Mock 企微</option><option value="trial_class">试听课</option><option value="learning_plan">学习方案</option><option value="other">其他</option></select></label>
          <label>计划时间<input v-model="interventionDueAt" type="datetime-local"></label>
          <label class="wide">内部备注<textarea v-model="interventionNote" maxlength="500" placeholder="可选；备注会加密保存"></textarea></label>
          <button type="button" :disabled="actionBusy || !interventionDueAt" @click="saveIntervention">创建人工跟进</button>
        </div>
        <div v-else class="form-row">
          <div><strong>当前状态：{{ selectedRisk.intervention.status }}</strong><p>计划：{{ formatDate(selectedRisk.intervention.due_at) }}</p></div>
          <template v-if="!['completed', 'cancelled'].includes(selectedRisk.intervention.status)">
            <label>人工结果<select v-model="interventionOutcome"><option value="retained">已稳定留存</option><option value="recovered">成功挽回</option><option value="churned">确认流失</option><option value="unknown">暂不确定</option></select></label>
            <button type="button" :disabled="actionBusy" @click="finishIntervention">确认完成</button>
          </template>
        </div>
        <p v-if="actionMessage" class="action-message">{{ actionMessage }}</p>
      </section>

      <section v-if="currentRole === 'admin'" class="model-panel">
        <div class="section-heading"><div><p class="eyebrow">Model Governance</p><h2>模型版本治理</h2></div><span>只允许已审批版本进入定时评分</span></div>
        <div class="form-grid">
          <label>版本号<input v-model="modelVersion" placeholder="例如 2026.09.20-v1"></label>
          <label>模型文件<input v-model="artifactFilename"></label>
          <label>评测报告<input v-model="reportFilename"></label>
          <button type="button" :disabled="actionBusy || !modelVersion" @click="saveModel">登记候选模型</button>
        </div>
        <div class="model-list">
          <article v-for="model in models" :key="model.id">
            <span><strong>{{ model.version }}</strong><small>{{ model.model_name }}</small></span>
            <b :data-status="model.status">{{ model.status }}</b>
            <button v-if="model.status === 'candidate'" type="button" :disabled="actionBusy" @click="approveModel(model.id)">审批使用</button>
          </article>
          <p v-if="!models.length" class="hint">尚未登记模型版本。</p>
        </div>
      </section>

      <section v-if="!batches.length" class="empty large">
        <strong>暂无评分批次</strong>
        <p>先运行离线批量评分脚本，完成的批次会显示在这里。</p>
      </section>
    </template>
  </div>
</template>

<style scoped>
.admin-page { display: grid; gap: 20px; }.page-header, .section-heading { display: flex; align-items: end; justify-content: space-between; gap: 20px; }.page-header h1, .section-heading h2 { margin: 0; }.page-header p:last-child, .section-heading > span, .state, .empty p { color: #64748b; }.eyebrow { margin: 0 0 6px; color: #7c3aed; font-size: 12px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
button { padding: 9px 14px; border: 0; border-radius: 9px; color: white; background: #2563eb; cursor: pointer; }button:disabled { cursor: wait; opacity: .55; }
.filters, .risk-filters { display: flex; flex-wrap: wrap; align-items: end; gap: 10px; padding: 16px; border: 1px solid #dbe5f3; border-radius: 14px; background: white; }.filters label, .risk-filters label { display: grid; gap: 5px; color: #64748b; font-size: 12px; }.filters input, .filters select, .risk-filters input, .risk-filters select { min-width: 150px; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 8px; font: inherit; }
.batch-panel, .risk-panel, .trace-panel, .action-panel, .model-panel, .empty.large { padding: 18px; border: 1px solid #dbe5f3; border-radius: 16px; background: white; box-shadow: 0 8px 22px rgb(30 64 175 / 5%); }.batch-list { display: grid; gap: 8px; margin-top: 14px; }.batch-card { display: flex; justify-content: space-between; width: 100%; padding: 12px 14px; color: #172033; text-align: left; border: 1px solid #e2e8f0; background: #f8fafc; }.batch-card.active { border-color: #2563eb; background: #eff6ff; box-shadow: 0 0 0 2px rgb(37 99 235 / 10%); }.batch-card span { display: grid; gap: 3px; }.batch-card span:last-child { text-align: right; }.batch-card small { color: #64748b; }.batch-card b { color: #166534; }.batch-card b[data-status="running"] { color: #1d4ed8; }.batch-card b[data-status="failed"] { color: #b91c1c; }
.summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }.summary-grid article { display: grid; gap: 8px; padding: 18px; border: 1px solid #dbe5f3; border-radius: 14px; background: white; }.summary-grid span { color: #64748b; font-size: 13px; }.summary-grid strong { font-size: 28px; }.summary-grid .high strong { color: #be123c; }.summary-grid .medium strong { color: #b45309; }.summary-grid .low strong { color: #15803d; }
.trace-panel { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 14px; }.trace-panel div { display: grid; gap: 6px; min-width: 0; }.trace-panel span { color: #64748b; font-size: 12px; }.trace-panel code { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.danger { color: #b91c1c; }
.risk-panel { display: grid; gap: 16px; }.table-wrap { overflow-x: auto; }table { width: 100%; min-width: 820px; border-collapse: collapse; }th, td { padding: 12px 10px; text-align: left; border-bottom: 1px solid #e2e8f0; }th { color: #475569; font-size: 13px; }td small { display: block; margin-top: 3px; color: #94a3b8; }td a { display: block; margin-top: 4px; color: #1d4ed8; }.risk-badge { padding: 5px 10px; border-radius: 999px; color: #166534; background: #dcfce7; font-size: 12px; font-weight: 800; }.risk-badge[data-level="high"] { color: #9f1239; background: #ffe4e6; }.risk-badge[data-level="medium"] { color: #92400e; background: #fef3c7; }.empty { padding: 24px; color: #64748b; text-align: center; }.empty.large strong { color: #1e3a8a; font-size: 18px; }.pagination { display: flex; align-items: center; justify-content: center; gap: 14px; }.pagination button, button.secondary { color: #1d4ed8; background: #eff6ff; }.error { color: #b91c1c; }.hint { color: #64748b; }.action-panel, .model-panel { display: grid; gap: 16px; }.form-row, .form-grid { display: flex; flex-wrap: wrap; align-items: end; gap: 12px; }.form-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)) auto; }.form-row label, .form-grid label { display: grid; gap: 5px; color: #64748b; font-size: 12px; }.form-row input, .form-row select, .form-grid input, .form-grid select, .form-grid textarea { padding: 9px; border: 1px solid #cbd5e1; border-radius: 8px; font: inherit; }.form-grid .wide { grid-column: 1 / -2; }.action-message { margin: 0; color: #1d4ed8; font-weight: 700; }.model-list { display: grid; gap: 8px; }.model-list article { display: flex; align-items: center; gap: 14px; padding: 12px; border: 1px solid #e2e8f0; border-radius: 10px; }.model-list article > span { display: grid; margin-right: auto; }.model-list small { color: #64748b; }.model-list b[data-status="approved"] { color: #15803d; }.model-list b[data-status="retired"] { color: #64748b; }
@media (max-width: 800px) { .summary-grid { grid-template-columns: repeat(2, 1fr); }.trace-panel, .form-grid { grid-template-columns: repeat(2, 1fr); }.page-header { align-items: flex-start; flex-direction: column; } }
</style>
