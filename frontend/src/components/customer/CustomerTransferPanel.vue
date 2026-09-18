<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { listCustomerTransfers, transferCustomer } from '../../api/customers'
import { listUsers, type AdminUser } from '../../api/users'
import type { Customer } from '../../types/customer'
import type { CustomerTransfer } from '../../types/customerTransfer'

const props = defineProps<{ customer: Customer }>()
const emit = defineEmits<{ transferred: [customer: Customer] }>()
const users = ref<AdminUser[]>([])
const transfers = ref<CustomerTransfer[]>([])
const targetId = ref<number | null>(null)
const reason = ref('')
const loading = ref(false)
const error = ref('')
const unavailable = ref(false)

async function load(): Promise<void> {
  error.value = ''
  try {
    const [userItems, history] = await Promise.all([listUsers(), listCustomerTransfers(props.customer.id)])
    users.value = userItems.filter((user) => user.is_active && user.id !== props.customer.owner_id)
    transfers.value = history
    unavailable.value = false
  } catch (reasonValue) {
    const message = reasonValue instanceof Error ? reasonValue.message : '转移数据加载失败'
    unavailable.value = message.includes('403')
    error.value = unavailable.value ? '当前角色没有客户转移权限。' : message
  }
}

async function submit(): Promise<void> {
  if (!targetId.value || loading.value) return
  loading.value = true; error.value = ''
  try {
    const customer = await transferCustomer(props.customer.id, targetId.value, reason.value)
    reason.value = ''; targetId.value = null
    emit('transferred', customer)
    await load()
  } catch (reasonValue) {
    error.value = reasonValue instanceof Error ? reasonValue.message : '客户转移失败'
  } finally { loading.value = false }
}

onMounted(load)
watch(() => props.customer.id, load)
</script>

<template>
  <section v-if="!unavailable" class="panel">
    <div class="heading"><div><p class="eyebrow">Ownership</p><h2>客户转移</h2></div><small>管理员 / 经理</small></div>
    <p v-if="error" class="error">{{ error }}</p>
    <form class="form" @submit.prevent="submit">
      <select v-model="targetId" required><option :value="null" disabled>选择新的负责人</option><option v-for="user in users" :key="user.id" :value="user.id">{{ user.username }}（{{ user.role }}）</option></select>
      <input v-model="reason" maxlength="500" placeholder="转移原因（可选）" />
      <button type="submit" :disabled="loading || !targetId">{{ loading ? '转移中…' : '确认转移' }}</button>
    </form>
    <details v-if="transfers.length"><summary>转移历史（{{ transfers.length }}）</summary><ul><li v-for="item in transfers" :key="item.id">{{ item.from_user_id ?? '未分配' }} → {{ item.to_user_id ?? '未分配' }} · {{ new Date(item.created_at).toLocaleString('zh-CN') }}<span v-if="item.reason"> · {{ item.reason }}</span></li></ul></details>
  </section>
</template>

<style scoped>
.panel { padding: 22px; border: 1px solid #e2e8f0; border-radius: 16px; background: white; }.heading { display:flex; justify-content:space-between; align-items:start; gap:10px; }.eyebrow { margin:0 0 6px; color:#7c3aed; font-size:12px; font-weight:700; letter-spacing:.1em; text-transform:uppercase; }h2 { margin:0 0 14px; }.heading small { color:#64748b; }.form { display:grid; grid-template-columns:1fr 1fr auto; gap:8px; }select,input { min-width:0; padding:9px; border:1px solid #cbd5e1; border-radius:8px; font:inherit; }button { padding:9px 12px; border:0; border-radius:8px; color:#fff; background:#7c3aed; cursor:pointer; }button:disabled { opacity:.5; cursor:wait; }.error { color:#b91c1c; }details { margin-top:14px; color:#64748b; font-size:13px; }ul { padding-left:18px; }@media(max-width:700px){.form{grid-template-columns:1fr;}}
</style>
