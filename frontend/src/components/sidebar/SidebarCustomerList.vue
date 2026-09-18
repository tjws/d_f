<script setup lang="ts">
import type { Customer } from '../../types/customer'

defineProps<{
  customers: Customer[]
  selectedId: number | null
  loading: boolean
}>()

const emit = defineEmits<{ select: [customerId: number] }>()

const stageLabels: Record<Customer['stage'], string> = {
  new: '新线索',
  following_up: '跟进中',
  converted: '已转化',
  lost: '已流失',
}
</script>

<template>
  <aside class="panel customer-list">
    <div class="panel-heading"><div><p>会话</p><span>客户列表</span></div><small>{{ customers.length }}</small></div>
    <p v-if="loading" class="muted">加载中…</p>
    <p v-else-if="customers.length === 0" class="muted">暂无客户。</p>
    <button v-for="customer in customers" :key="customer.id" type="button" class="customer-item" :class="{ active: customer.id === selectedId }" @click="emit('select', customer.id)">
      <span class="avatar">{{ customer.name.slice(0, 1) }}</span>
      <span class="customer-copy"><strong>{{ customer.name }}</strong><small>{{ customer.student_name || '未填写学生' }} · {{ stageLabels[customer.stage] }}</small></span>
      <i v-if="customer.stage === 'following_up'" aria-label="跟进中" />
    </button>
  </aside>
</template>

<style scoped>
.panel { padding: 16px; border: 1px solid #dbe3f0; border-radius: 14px; background: white; }
.panel-heading { display: flex; align-items: center; justify-content: space-between; margin: 0 5px 12px; color: #172033; }.panel-heading p { margin: 0 0 2px; color: #8b98aa; font-size: 11px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }.panel-heading span { font-size: 16px; font-weight: 800; }.panel-heading small { display: grid; width: 22px; height: 22px; place-items: center; border-radius: 50%; color: #64748b; background: #edf1f6; font-size: 11px; font-weight: 700; }.muted, .customer-item small { color: #718096; font-weight: 400; }
.customer-item { display: flex; align-items: center; gap: 9px; width: 100%; margin: 3px 0; padding: 10px 9px; border: 1px solid transparent; border-radius: 9px; text-align: left; background: transparent; cursor: pointer; }.customer-item:hover { background: #eef4fc; }.customer-item.active { border-color: #d5e6ff; background: #e9f2ff; }.avatar { display: grid; width: 34px; height: 34px; flex: 0 0 auto; place-items: center; border-radius: 11px; color: #1d4ed8; background: linear-gradient(135deg, #dcecff, #f2f7ff); font-size: 14px; font-weight: 800; }.customer-copy { display: grid; min-width: 0; flex: 1; gap: 3px; }.customer-item strong, .customer-item small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.customer-item strong { color: #25334a; }.customer-item small { font-size: 11px; }.customer-item i { width: 7px; height: 7px; border-radius: 50%; background: #07c160; box-shadow: 0 0 0 3px rgb(7 193 96 / 12%); }
</style>
