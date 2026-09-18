<script setup lang="ts">
import { ref } from 'vue'
import type { CourseOrder, CourseOrderCreate, CourseOrderStatus } from '../../types/courseOrder'

const props = defineProps<{ orders: CourseOrder[]; error?: string }>()
const emit = defineEmits<{ create: [payload: CourseOrderCreate]; update: [orderId: number, status: CourseOrderStatus] }>()
const externalId = ref('')
const courseName = ref('')
const amount = ref('0.00')
const status = ref<CourseOrderStatus>('intent')
const labels: Record<string, string> = { intent: '意向', pending_payment: '待支付', paid: '已支付', cancelled: '已取消', completed: '已完成' }

function create(): void {
  if (!externalId.value.trim() || !courseName.value.trim()) return
  emit('create', { external_order_id: externalId.value.trim(), course_name: courseName.value.trim(), amount: amount.value, status: status.value })
  externalId.value = ''
  courseName.value = ''
  amount.value = '0.00'
  status.value = 'intent'
}
</script>

<template>
  <section class="panel">
    <div class="heading"><div><p class="eyebrow">Orders</p><h2>课程订单</h2></div><span>{{ props.orders.length }} 条</span></div>
    <p v-if="props.error" class="error">{{ props.error }}</p>
    <div class="form-grid">
      <input v-model="externalId" placeholder="Mock 外部订单号" />
      <input v-model="courseName" placeholder="课程名称" />
      <input v-model="amount" type="number" min="0" step="0.01" placeholder="金额" />
      <select v-model="status"><option v-for="(_, key) in labels" :key="key" :value="key">{{ labels[key] }}</option></select>
      <button type="button" @click="create">新增订单</button>
    </div>
    <div v-for="order in props.orders" :key="order.id" class="item">
      <div><strong>{{ order.course_name }}</strong><p>{{ order.external_order_id }} · ¥{{ order.amount }} · {{ labels[order.status] ?? order.status }}</p></div>
      <select :value="order.status" @change="emit('update', order.id, ($event.target as HTMLSelectElement).value as CourseOrderStatus)">
        <option v-for="(_, key) in labels" :key="key" :value="key">{{ labels[key] }}</option>
      </select>
    </div>
    <p v-if="props.orders.length === 0" class="muted">暂无订单，可新增一条 Mock 订单。</p>
  </section>
</template>

<style scoped>
.panel { padding: 22px; border: 1px solid #e2e8f0; border-radius: 16px; background: white; }
.heading, .item { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.heading { margin-bottom: 12px; } .heading span { color: #64748b; }
.eyebrow { margin: 0 0 6px; color: #2563eb; font-size: 12px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
h2 { margin: 0; } .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
input, select, button { box-sizing: border-box; width: 100%; padding: 9px; border: 1px solid #cbd5e1; border-radius: 8px; font: inherit; }
button { color: white; background: #2563eb; cursor: pointer; } .item { margin-top: 10px; padding: 12px; border-radius: 10px; background: #eff6ff; }
.item select { width: auto; } p { margin: 5px 0 0; color: #64748b; } .muted { color: #64748b; } .error { color: #dc2626; }
</style>
