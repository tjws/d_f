<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getBusinessDashboard, type BusinessDashboard } from '../../api/businessDashboard'

const data = ref<BusinessDashboard | null>(null)
const loading = ref(true)
const error = ref('')
const start = ref('')
const end = ref('')
const forbidden = ref(false)
const stageLabels: Record<string, string> = { new: '新客户', following_up: '跟进中', converted: '已转化', lost: '已流失' }
const orderLabels: Record<string, string> = { intent: '意向', pending_payment: '待支付', paid: '已支付', completed: '已完成', cancelled: '已取消' }
const ticketLabels: Record<string, string> = { open: '开放', in_progress: '处理中', resolved: '已解决', closed: '已关闭' }

function isoStart(value: string): string | undefined { return value ? `${value}T00:00:00Z` : undefined }
function isoEnd(value: string): string | undefined { return value ? `${value}T23:59:59Z` : undefined }
function label(map: Record<string, string>, value: string): string { return map[value] || value }

async function load(): Promise<void> {
  loading.value = true; error.value = ''; forbidden.value = false
  try { data.value = await getBusinessDashboard({ start: isoStart(start.value), end: isoEnd(end.value) }) }
  catch (reason) { error.value = reason instanceof Error ? reason.message : '经营看板请求失败'; forbidden.value = error.value.includes('403') || error.value.includes('权限') }
  finally { loading.value = false }
}

onMounted(load)
</script>

<template>
  <div class="admin-page">
    <header class="page-header"><div><p class="eyebrow">Business Operations</p><h1>业务经营看板</h1><p>客户阶段、订单、工单和顾问工作量的可解释汇总，默认统计最近 7 天。</p></div><div class="filters"><label>开始日期<input v-model="start" type="date"></label><label>结束日期<input v-model="end" type="date"></label><button :disabled="loading" @click="load">{{ loading ? '加载中…' : '刷新' }}</button></div></header>
    <p v-if="loading">加载中…</p><p v-else-if="error" class="error">{{ forbidden ? '当前角色无权查看经营看板。' : error }}</p><p v-else-if="!data" class="empty">暂无数据。</p>
    <template v-else>
      <section class="cards"><article><span>客户数</span><strong>{{ data.customer_total }}</strong></article><article><span>订单数</span><strong>{{ data.orders.total }}</strong></article><article><span>已支付/完成</span><strong>{{ data.orders.paid_or_completed }}</strong></article><article><span>支付金额</span><strong>¥{{ data.orders.paid_amount.toFixed(2) }}</strong></article><article><span>开放工单</span><strong>{{ data.tickets.open_count }}</strong></article><article><span>复购/续费近似率</span><strong>{{ (data.renewal_rate * 100).toFixed(1) }}%</strong></article></section>
      <section class="grid-two"><div class="panel"><h2>客户转化漏斗</h2><table><thead><tr><th>阶段</th><th>客户数</th></tr></thead><tbody><tr v-for="item in data.funnel" :key="item.stage"><td>{{ stageLabels[item.stage] || item.stage }}</td><td>{{ item.count }}</td></tr></tbody></table></div><div class="panel"><h2>订单状态</h2><table><thead><tr><th>状态</th><th>数量</th></tr></thead><tbody><tr v-for="(count, status) in data.orders.by_status" :key="status"><td>{{ label(orderLabels, status) }}</td><td>{{ count }}</td></tr></tbody></table></div></section>
      <section class="grid-two"><div class="panel"><h2>服务工单</h2><table><thead><tr><th>状态</th><th>数量</th></tr></thead><tbody><tr v-for="(count, status) in data.tickets.by_status" :key="status"><td>{{ label(ticketLabels, status) }}</td><td>{{ count }}</td></tr></tbody></table></div><div class="panel"><h2>复购/续费口径</h2><p>{{ data.renewal_rate_definition }}</p><p>付费客户 {{ data.paying_customer_count }}，重复付费客户 {{ data.repeat_purchase_customer_count }}。</p></div></section>
      <section class="panel"><h2>顾问人效</h2><p class="muted">按时间范围内新增客户、已转化客户、已支付金额和开放工单汇总；没有数据的 active 销售/经理也会展示。</p><table><thead><tr><th>顾问</th><th>客户数</th><th>已转化</th><th>支付金额</th><th>开放工单</th></tr></thead><tbody><tr v-for="item in data.owner_efficiency" :key="item.user_id"><td>{{ item.full_name || item.username }}</td><td>{{ item.customer_count }}</td><td>{{ item.converted_customer_count }}</td><td>¥{{ item.paid_amount.toFixed(2) }}</td><td>{{ item.open_ticket_count }}</td></tr></tbody></table><p v-if="!data.owner_efficiency.length" class="empty">暂无 active 销售或经理。</p></section>
    </template>
  </div>
</template>

<style scoped>
.admin-page { display: grid; gap: 20px; }
.page-header { display: flex; justify-content: space-between; gap: 18px; }
.eyebrow { margin: 0 0 6px; color: #0f766e; font-size: 12px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
.page-header h1 { margin: 0; }
.page-header p:last-child, .muted, .empty { color: #64748b; }
.filters { display: flex; align-items: end; gap: 8px; }
.filters label { display: grid; gap: 4px; color: #64748b; font-size: 12px; }
.filters input { padding: 7px 8px; border: 1px solid #cbd5e1; border-radius: 7px; }
.filters button { padding: 8px 12px; border: 0; border-radius: 8px; color: #fff; background: #0f766e; cursor: pointer; }
.filters button:disabled { opacity: .6; }
.cards { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; }
.cards article, .panel { padding: 18px; border: 1px solid #dbe5ee; border-radius: 16px; background: #fff; box-shadow: 0 8px 22px rgb(15 118 110 / 5%); }
.cards span { display: block; color: #64748b; font-size: 12px; }
.cards strong { display: block; margin-top: 8px; color: #0f766e; font-size: 25px; }
.grid-two { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.panel h2 { margin-top: 0; font-size: 18px; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 9px 7px; text-align: left; border-bottom: 1px solid #e2e8f0; }
th { color: #475569; font-size: 12px; }
.error { color: #b91c1c; }
@media (max-width: 1050px) { .cards { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 800px) { .page-header, .filters { flex-direction: column; align-items: stretch; }.cards, .grid-two { grid-template-columns: 1fr 1fr; } }
</style>
