<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getAIDashboard } from '../../api/aiDashboard'
import type { AIDashboard } from '../../types/aiDashboard'

const data = ref<AIDashboard | null>(null)
const loading = ref(true)
const error = ref('')
const start = ref('')
const end = ref('')
const forbidden = ref(false)

function isoStart(value: string): string | undefined { return value ? `${value}T00:00:00Z` : undefined }
function isoEnd(value: string): string | undefined { return value ? `${value}T23:59:59Z` : undefined }

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  forbidden.value = false
  try {
    data.value = await getAIDashboard({ start: isoStart(start.value), end: isoEnd(end.value) })
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '看板请求失败'
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
      <p class="eyebrow">AI Governance</p>
      <h1>AI 采用率看板</h1>
      <p>统计最近 7 天的建议处理与工作流结果；数据由后端汇总。</p>
      <div class="filters"><label>开始日期<input v-model="start" type="date"></label><label>结束日期<input v-model="end" type="date"></label><button type="button" :disabled="loading" @click="load">{{ loading ? '加载中…' : '刷新指标' }}</button></div>
    </header>
    <p v-if="loading">加载中…</p>
    <p v-else-if="error" class="error">{{ forbidden ? '当前角色无权查看 AI 管理看板。' : error }}</p>
    <p v-else-if="!data" class="empty">暂无数据。</p>
    <template v-else>
      <section class="cards">
        <article><span>建议总数</span><strong>{{ data.suggestions_total }}</strong></article>
        <article><span>反馈总数</span><strong>{{ data.feedback_total }}</strong></article>
        <article><span>采用率</span><strong>{{ (data.adoption_rate * 100).toFixed(1) }}%</strong></article>
        <article><span>百炼调用</span><strong>{{ data.bailian_calls }}</strong></article><article><span>百炼失败</span><strong class="danger-number">{{ data.bailian_failures }}</strong></article>
        <article><span>RAG fallback</span><strong>{{ (data.rag_fallback_rate * 100).toFixed(1) }}%</strong></article>
        <article><span>Agent 推理失败</span><strong class="danger-number">{{ data.agent_reasoning_failures }}</strong></article>
        <article><span>平均任务耗时</span><strong>{{ data.avg_task_duration_ms }} ms</strong></article>
      </section>
      <section class="panel">
        <h2>人工处理</h2>
        <p>接受 {{ data.accepted }} · 编辑 {{ data.edited }} · 拒绝 {{ data.rejected }}</p>
      </section>
      <section class="panel">
        <h2>工作流</h2>
        <p>成功 {{ data.workflow.succeeded }} · 失败 {{ data.workflow.failed }} · 等待人工 {{ data.workflow.waiting_human }}</p>
      </section>
      <section class="panel">
        <h2>RAG 与 Agent 治理</h2>
        <p>RAG 查询 {{ data.rag_queries_total }} 次，fallback {{ data.rag_fallbacks }} 次；Agent 反馈 {{ data.agent_feedback_total }} 条。</p>
        <p>反馈分类：推理问题 {{ data.agent_feedback_by_action.incorrect_reasoning || 0 }} · 信息不全 {{ data.agent_feedback_by_action.missing_information || 0 }} · 不实用 {{ data.agent_feedback_by_action.not_useful || 0 }}</p>
        <p>推理失败率 {{ (data.agent_reasoning_failure_rate * 100).toFixed(1) }}%，平均任务耗时 {{ data.avg_task_duration_ms }} ms。</p>
      </section>
      <section class="panel">
        <h2>按建议类型</h2>
        <table><thead><tr><th>类型</th><th>建议</th><th>接受</th><th>编辑</th><th>拒绝</th></tr></thead>
          <tbody><tr v-for="(item, type) in data.by_suggestion_type" :key="type"><td>{{ type }}</td><td>{{ item.suggestions }}</td><td>{{ item.accepted }}</td><td>{{ item.edited }}</td><td>{{ item.rejected }}</td></tr></tbody>
        </table>
      </section>
    </template>
  </div>
</template>

<style scoped>
.admin-page { display: grid; gap: 22px; }
.page-header { color: #1f2937; }
.eyebrow { margin: 0 0 6px; color: #7c3aed; font-size: 12px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
.page-header h1 { margin: 0; }
.page-header p:last-child, .empty { color: #64748b; }
.error { color: #b91c1c; }
.cards { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; }
.cards article, .panel { padding: 20px; border: 1px solid #e2e8f0; border-radius: 16px; background: rgb(255 255 255 / 94%); box-shadow: 0 8px 22px rgb(30 64 175 / 5%); }
.cards span { display: block; color: #64748b; font-size: 13px; } .cards strong { display: block; margin-top: 8px; color: #1d4ed8; font-size: 30px; }
.danger-number { color: #be123c !important; }
.filters { display: flex; flex-wrap: wrap; align-items: end; gap: 10px; margin-top: 16px; }.filters label { display: grid; gap: 4px; color: #64748b; font-size: 12px; }.filters input { padding: 7px 8px; border: 1px solid #cbd5e1; border-radius: 7px; }.filters button { padding: 8px 12px; border: 0; border-radius: 8px; color: white; background: #2563eb; cursor: pointer; }.filters button:disabled { opacity: .6; cursor: wait; }
.panel h2 { margin-top: 0; font-size: 18px; } table { width: 100%; border-collapse: collapse; } th, td { padding: 10px; text-align: left; border-bottom: 1px solid #e2e8f0; } th { color: #475569; font-size: 13px; }
@media (max-width: 1000px) { .cards { grid-template-columns: repeat(3, 1fr); } }@media (max-width: 800px) { .cards { grid-template-columns: repeat(2, 1fr); } }
</style>
