<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { getAdminOperations, mockSyncOperations, type AdminOperations } from '../../api/adminOperations'

const data = ref<AdminOperations | null>(null)
const loading = ref(true)
const error = ref('')
const tab = ref<'orders' | 'tickets'>('orders')
const orderStatus = ref('')
const ticketStatus = ref('')
const syncCustomerId = ref<number | null>(null)
const syncing = ref(false)
const syncSuccess = ref('')

const orderLabels: Record<string, string> = { intent: '意向', pending_payment: '待支付', paid: '已支付', completed: '已完成', cancelled: '已取消' }
const ticketLabels: Record<string, string> = { open: '开放', in_progress: '处理中', resolved: '已解决', closed: '已关闭' }

function label(map: Record<string, string>, value: string): string { return map[value] || value }
function money(value: string | number): string { return Number(value).toFixed(2) }
function date(value: string): string { return new Date(value).toLocaleString('zh-CN') }

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    data.value = await getAdminOperations({ order_status: orderStatus.value || undefined, ticket_status: ticketStatus.value || undefined, limit: 100 })
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '订单和工单加载失败'
  } finally {
    loading.value = false
  }
}

function clearFilters(): void {
  orderStatus.value = ''
  ticketStatus.value = ''
  void load()
}

async function syncDemoOperations(): Promise<void> {
  if (!syncCustomerId.value) return
  syncing.value = true
  error.value = ''
  syncSuccess.value = ''
  try {
    const result = await mockSyncOperations({
      customer_id: syncCustomerId.value,
      orders: [{ external_order_id: `mock-sync-order-${syncCustomerId.value}`, course_name: '同步演练课程', amount: '999.00', status: 'pending_payment' }],
      tickets: [{ external_ticket_id: `mock-sync-ticket-${syncCustomerId.value}`, type: '同步演练', summary: '本地 Mock 外部工单' }],
    })
    syncSuccess.value = `Mock 同步完成：新增订单 ${result.orders_created} 条、工单 ${result.tickets_created} 条；重复项已跳过。`
    await load()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : 'Mock 同步失败'
  } finally {
    syncing.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="admin-page">
    <header class="page-header"><div><p class="eyebrow">Operations Desk</p><h1>订单与工单</h1><p>统一回溯课程订单和服务工单；编辑动作仍在客户工作台完成。</p></div><button type="button" :disabled="loading" @click="load">{{ loading ? '加载中…' : '刷新' }}</button></header>
    <section class="filters panel"><label>订单状态<select v-model="orderStatus"><option value="">全部</option><option v-for="(text, key) in orderLabels" :key="key" :value="key">{{ text }}</option></select></label><label>工单状态<select v-model="ticketStatus"><option value="">全部</option><option v-for="(text, key) in ticketLabels" :key="key" :value="key">{{ text }}</option></select></label><button type="button" @click="load">应用筛选</button><button type="button" class="secondary" @click="clearFilters">清除</button></section>
    <section class="panel sync-panel"><h2>Mock 外部同步演练</h2><p class="muted">输入已有客户 ID，生成一条本地订单和工单；重复演练只会跳过相同外部编号。</p><div class="sync-form"><input v-model.number="syncCustomerId" type="number" min="1" placeholder="客户 ID"><button type="button" :disabled="syncing || !syncCustomerId" @click="syncDemoOperations">{{ syncing ? '同步中…' : '同步演练数据' }}</button></div><p v-if="syncSuccess" class="success">{{ syncSuccess }}</p></section>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-else-if="loading" class="muted">正在读取业务记录…</p>
    <template v-else-if="data">
      <nav class="tabs"><button type="button" :class="{ active: tab === 'orders' }" @click="tab = 'orders'">订单（{{ data.orders.length }}）</button><button type="button" :class="{ active: tab === 'tickets' }" @click="tab = 'tickets'">工单（{{ data.tickets.length }}）</button></nav>
      <section class="panel table-wrap" v-if="tab === 'orders'"><table><thead><tr><th>客户</th><th>课程</th><th>金额</th><th>状态</th><th>负责人</th><th>下单时间</th></tr></thead><tbody><tr v-for="order in data.orders" :key="order.id"><td><RouterLink :to="`/customers/${order.customer_id}`">{{ order.customer_name }}</RouterLink><small>{{ order.external_order_id }}</small></td><td>{{ order.course_name }}</td><td>¥{{ money(order.amount) }}</td><td><span class="status order">{{ label(orderLabels, order.status) }}</span></td><td>{{ order.owner_name || '未分配' }}</td><td>{{ date(order.ordered_at) }}</td></tr></tbody></table><p v-if="!data.orders.length" class="muted">没有符合条件的订单。</p></section>
      <section class="panel table-wrap" v-else><table><thead><tr><th>客户</th><th>类型</th><th>摘要</th><th>状态</th><th>负责人</th><th>开启时间</th></tr></thead><tbody><tr v-for="ticket in data.tickets" :key="ticket.id"><td><RouterLink :to="`/customers/${ticket.customer_id}`">{{ ticket.customer_name }}</RouterLink><small>{{ ticket.external_ticket_id }}</small></td><td>{{ ticket.type }}</td><td class="summary">{{ ticket.summary }}</td><td><span class="status ticket">{{ label(ticketLabels, ticket.status) }}</span></td><td>{{ ticket.owner_name || '未分配' }}</td><td>{{ date(ticket.opened_at) }}</td></tr></tbody></table><p v-if="!data.tickets.length" class="muted">没有符合条件的工单。</p></section>
    </template>
  </div>
</template>

<style scoped>
.admin-page { display: grid; gap: 18px; }.page-header { display: flex; align-items: end; justify-content: space-between; gap: 20px; }.page-header h1 { margin: 0; }.page-header p:last-child, .muted { color: #64748b; }.eyebrow { margin: 0 0 6px; color: #0f766e; font-size: 12px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }button { padding: 9px 14px; border: 0; border-radius: 8px; color: white; background: #0f766e; cursor: pointer; }button:disabled { cursor: wait; opacity: .6; }.panel { padding: 18px; border: 1px solid #dbe5ee; border-radius: 16px; background: white; box-shadow: 0 8px 22px rgb(15 118 110 / 5%); }.filters { display: flex; align-items: end; flex-wrap: wrap; gap: 10px; }.filters label { display: grid; gap: 4px; color: #475569; font-size: 13px; }.filters select { min-width: 140px; padding: 8px; border: 1px solid #cbd5e1; border-radius: 8px; background: white; }.secondary { color: #475569; background: #e2e8f0; }.tabs { display: flex; gap: 8px; }.tabs button { color: #475569; background: #e2e8f0; }.tabs button.active { color: white; background: #0f766e; }.table-wrap { overflow-x: auto; }table { width: 100%; border-collapse: collapse; }th, td { padding: 11px 8px; text-align: left; border-bottom: 1px solid #e2e8f0; white-space: nowrap; }th { color: #475569; font-size: 12px; }td small { display: block; margin-top: 3px; color: #94a3b8; font-size: 12px; }td a { color: #0f766e; font-weight: 700; text-decoration: none; }.summary { max-width: 320px; white-space: normal; }.status { padding: 4px 8px; border-radius: 999px; font-size: 12px; }.status.order { color: #1d4ed8; background: #dbeafe; }.status.ticket { color: #9a3412; background: #ffedd5; }.error { color: #b91c1c; }.sync-panel h2 { margin: 0 0 6px; }.sync-form { display: flex; gap: 8px; }.sync-form input { width: 150px; padding: 9px; border: 1px solid #cbd5e1; border-radius: 8px; }.success { color: #047857; }@media (max-width: 700px) { .page-header { align-items: flex-start; flex-direction: column; }.filters { align-items: stretch; flex-direction: column; }.filters label, .filters select { width: 100%; } }
</style>
