<script setup lang="ts">
import { onMounted, ref } from 'vue'
import {
  getRAGEvaluationReport,
  listRAGEvaluationCases,
  reviewRAGEvaluationCase,
  type RAGEvaluationCase,
  type RAGEvaluationCaseStatus,
  type RAGEvaluationReport,
} from '../../api/knowledge'
import { useAuth } from '../../composables/useAuth'

const { currentRole } = useAuth()
const report = ref<RAGEvaluationReport | null>(null)
const cases = ref<RAGEvaluationCase[]>([])
const filter = ref<RAGEvaluationCaseStatus | ''>('open')
const loading = ref(true)
const savingId = ref<number | null>(null)
const error = ref('')
const notice = ref('')

function statusLabel(status: RAGEvaluationCaseStatus): string {
  return ({ open: '待复核', reviewed: '已复核', ignored: '已忽略' })[status]
}

function expectedText(item: RAGEvaluationCase): string {
  return item.expected_document_ids?.join(', ') || ''
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    report.value = await getRAGEvaluationReport(3)
    cases.value = await listRAGEvaluationCases(filter.value || undefined)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : 'RAG 评测数据加载失败'
  } finally {
    loading.value = false
  }
}

async function save(item: RAGEvaluationCase, status: RAGEvaluationCaseStatus): Promise<void> {
  savingId.value = item.id
  error.value = ''
  notice.value = ''
  try {
    const expected = expectedText(item).split(',').map((value) => value.trim()).filter(Boolean)
    await reviewRAGEvaluationCase(item.id, {
      status,
      expected_document_ids: expected,
      review_note: item.review_note || undefined,
    })
    notice.value = `用例 #${item.id} 已${statusLabel(status)}`
    await load()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '评测用例保存失败'
  } finally {
    savingId.value = null
  }
}

async function changeFilter(): Promise<void> {
  await load()
}

onMounted(load)
</script>

<template>
  <div class="admin-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">RAG Evaluation Loop</p>
        <h1>RAG 评测闭环</h1>
        <p>把 fallback 和人工反馈沉淀为可复核用例，再用只读检索评测确认改进效果。</p>
      </div>
      <span class="role-badge">{{ currentRole || '未知角色' }}</span>
    </header>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>
    <p v-if="loading">加载中…</p>

    <template v-else>
      <section v-if="report" class="cards">
        <article><span>待复核</span><strong>{{ report.queue.open }}</strong></article>
        <article><span>已复核</span><strong>{{ report.queue.reviewed }}</strong></article>
        <article><span>fallback 用例</span><strong>{{ report.queue.fallback }}</strong></article>
        <article><span>向量 Hit@3</span><strong>{{ (report.fixed_evaluation.summary.vector.hit_at_k * 100).toFixed(0) }}%</strong></article>
        <article><span>向量 MRR</span><strong>{{ report.fixed_evaluation.summary.vector.mean_reciprocal_rank.toFixed(2) }}</strong></article>
      </section>

      <section class="panel">
        <div class="panel-head">
          <div><h2>人工复核队列</h2><p>只有 admin / manager 可以查看和修改；sales 后端会被拒绝。</p></div>
          <label>状态<select v-model="filter" @change="changeFilter"><option value="open">待复核</option><option value="reviewed">已复核</option><option value="ignored">已忽略</option><option value="">全部</option></select></label>
        </div>
        <p v-if="!cases.length" class="empty">当前筛选没有评测用例。产生 fallback 或提交 Agent 反馈后会自动进入队列。</p>
        <div v-else class="case-list">
          <article v-for="item in cases" :key="item.id" class="case-card">
            <div class="case-head"><div><strong>#{{ item.id }} · {{ item.source_type }}</strong><span>{{ item.retrieval_mode || '未执行 RAG' }}<span v-if="item.fallback"> · fallback</span></span></div><span class="status" :data-status="item.status">{{ statusLabel(item.status) }}</span></div>
            <p class="query">{{ item.query_excerpt || '该 Agent 反馈没有可展示的原始查询摘要' }}</p>
            <p class="meta">来源 {{ item.source_id }} · 产生于 {{ new Date(item.created_at).toLocaleString() }}</p>
            <label>期望命中文档 slug（逗号分隔）<input :value="expectedText(item)" :placeholder="expectedText(item) || '例如 03_pricing_faq'" @input="(event) => { item.expected_document_ids = (event.target as HTMLInputElement).value.split(',').map((value) => value.trim()).filter(Boolean) }"></label>
            <label>复核备注<textarea v-model="item.review_note" rows="2" placeholder="记录为什么命中或需要补充哪类知识"></textarea></label>
            <div class="actions"><button :disabled="savingId === item.id" @click="save(item, 'reviewed')">标记已复核</button><button class="secondary" :disabled="savingId === item.id" @click="save(item, 'ignored')">忽略</button><button v-if="item.status !== 'open'" class="ghost" :disabled="savingId === item.id" @click="save(item, 'open')">重新打开</button></div>
          </article>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.admin-page { display: grid; gap: 20px; }.page-header { display: flex; justify-content: space-between; gap: 16px; }.page-header h1 { margin: 0; }.eyebrow { margin: 0 0 6px; color: #0f766e; font-size: 12px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }.page-header p:last-child, .empty, .meta { color: #64748b; }.role-badge, .status { align-self: flex-start; padding: 6px 10px; border-radius: 999px; color: #1d4ed8; background: #dbeafe; font-size: 12px; }.status[data-status="reviewed"] { color: #166534; background: #dcfce7; }.status[data-status="ignored"] { color: #64748b; background: #e2e8f0; }.cards { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }.cards article, .panel { padding: 18px; border: 1px solid #dbe5f3; border-radius: 16px; background: #fff; box-shadow: 0 8px 22px rgb(30 64 175 / 5%); }.cards span { display: block; color: #64748b; font-size: 13px; }.cards strong { display: block; margin-top: 8px; color: #1d4ed8; font-size: 28px; }.panel-head, .case-head { display: flex; justify-content: space-between; gap: 14px; }.panel h2 { margin: 0; }.panel-head p { color: #64748b; }.panel-head label { display: grid; gap: 5px; color: #64748b; font-size: 12px; }.panel-head select, input, textarea { padding: 8px; border: 1px solid #cbd5e1; border-radius: 8px; font: inherit; }.case-list { display: grid; gap: 12px; }.case-card { padding: 15px; border: 1px solid #dbe5f3; border-radius: 12px; background: #f8fbff; }.case-head div { display: grid; gap: 3px; }.case-head div span { color: #64748b; font-size: 12px; }.query { margin: 14px 0 6px; color: #0f172a; line-height: 1.55; }.meta { margin: 0 0 12px; font-size: 12px; }.case-card label { display: grid; gap: 5px; margin-top: 9px; color: #475569; font-size: 12px; }.actions { display: flex; gap: 8px; margin-top: 12px; }button { padding: 8px 12px; border: 0; border-radius: 8px; color: #fff; background: #2563eb; cursor: pointer; }button:disabled { opacity: .5; cursor: not-allowed; }.secondary { color: #92400e; background: #fef3c7; }.ghost { color: #1e40af; background: #eff6ff; }.error { color: #b91c1c; }.notice { color: #166534; }@media (max-width: 900px) { .cards { grid-template-columns: repeat(3, 1fr); } }@media (max-width: 650px) { .cards { grid-template-columns: repeat(2, 1fr); }.page-header, .panel-head, .case-head { flex-direction: column; } }
</style>
