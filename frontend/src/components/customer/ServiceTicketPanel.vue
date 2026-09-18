<script setup lang="ts">
import { ref } from 'vue'
import type { ServiceTicket, ServiceTicketCreate, ServiceTicketStatus } from '../../types/serviceTicket'

const props = defineProps<{ tickets: ServiceTicket[]; error?: string }>()
const emit = defineEmits<{ create: [payload: ServiceTicketCreate]; update: [ticketId: number, status: ServiceTicketStatus] }>()
const externalId = ref('')
const type = ref('general')
const summary = ref('')
const labels: Record<string, string> = { open: '待处理', in_progress: '处理中', resolved: '已解决', closed: '已关闭' }

function create(): void {
  if (!externalId.value.trim() || !summary.value.trim()) return
  emit('create', { external_ticket_id: externalId.value.trim(), type: type.value.trim() || 'general', summary: summary.value.trim() })
  externalId.value = ''; summary.value = ''; type.value = 'general'
}
</script>

<template>
  <section class="panel">
    <div class="heading"><div><p class="eyebrow">Service</p><h2>服务工单</h2></div><span>{{ props.tickets.length }} 条</span></div>
    <p v-if="props.error" class="error">{{ props.error }}</p>
    <div class="form-grid"><input v-model="externalId" placeholder="Mock 外部工单号" /><input v-model="type" placeholder="工单类型" /><textarea v-model="summary" rows="2" placeholder="问题摘要" /><button type="button" @click="create">新增工单</button></div>
    <div v-for="ticket in props.tickets" :key="ticket.id" class="item">
      <div><strong>{{ ticket.type }}</strong><p>{{ ticket.summary }}</p><small>{{ ticket.external_ticket_id }} · {{ labels[ticket.status] ?? ticket.status }}</small></div>
      <select :value="ticket.status" @change="emit('update', ticket.id, ($event.target as HTMLSelectElement).value as ServiceTicketStatus)"><option v-for="(_, key) in labels" :key="key" :value="key">{{ labels[key] }}</option></select>
    </div>
    <p v-if="props.tickets.length === 0" class="muted">暂无工单，可新增一条 Mock 服务记录。</p>
  </section>
</template>

<style scoped>
.panel { padding: 22px; border: 1px solid #e2e8f0; border-radius: 16px; background: white; }
.heading, .item { display: flex; align-items: center; justify-content: space-between; gap: 12px; } .heading { margin-bottom: 12px; } .heading span { color: #64748b; }
.eyebrow { margin: 0 0 6px; color: #0f766e; font-size: 12px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; } h2 { margin: 0; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; } textarea { grid-column: 1 / -1; resize: vertical; }
input, textarea, select, button { box-sizing: border-box; width: 100%; padding: 9px; border: 1px solid #cbd5e1; border-radius: 8px; font: inherit; } button { color: white; background: #0f766e; cursor: pointer; }
.item { margin-top: 10px; padding: 12px; border-radius: 10px; background: #f0fdfa; } .item select { width: auto; } p { margin: 5px 0; color: #475569; } small { color: #64748b; } .muted { color: #64748b; } .error { color: #dc2626; }
</style>
