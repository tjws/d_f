<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { listCustomers } from '../api/customers'
import type { Customer } from '../types/customer'
import CustomerCreateForm from '../components/customer/CustomerCreateForm.vue'

const customers = ref<Customer[]>([])
const loading = ref(true)
const errorMessage = ref('')
const showCreateForm = ref(false)
const total = ref(0)
const route = useRoute()

const stageLabels: Record<Customer['stage'], string> = {
  new: '新客户',
  following_up: '跟进中',
  converted: '已转化',
  lost: '已流失',
}

const stageOptions: Array<{ value: Customer['stage']; label: string }> = [
  { value: 'new', label: '新客户' },
  { value: 'following_up', label: '跟进中' },
  { value: 'converted', label: '已转化' },
  { value: 'lost', label: '已流失' },
]

function stageFromQuery(value: unknown): Customer['stage'] | undefined {
  const candidate = Array.isArray(value) ? value[0] : value
  return stageOptions.some((option) => option.value === candidate)
    ? candidate as Customer['stage']
    : undefined
}

const selectedStage = ref<Customer['stage'] | undefined>(stageFromQuery(route.query.stage))

function formatDate(value: string | null): string {
  if (!value) {
    return '未设置'
  }

  return new Date(value).toLocaleString('zh-CN')
}

async function loadCustomers(): Promise<void> {
  loading.value = true
  errorMessage.value = ''

  try {
    const response = await listCustomers({
      page: 1,
      page_size: 20,
      stage: selectedStage.value,
    })

    customers.value = response.items
    total.value = response.total
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : '客户列表加载失败'
  } finally {
    loading.value = false
  }
}

async function handleCustomerCreated(): Promise<void> {
  showCreateForm.value = false
  await loadCustomers()
}

onMounted(loadCustomers)

watch(() => route.query.stage, (value) => {
  selectedStage.value = stageFromQuery(value)
  void loadCustomers()
})
</script>

<template>
  <main class="customer-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Customer Workspace</p>
        <h1>客户列表</h1>
        <p class="description">
          浏览、筛选并进入客户工作台；客户数据与访问范围由后端统一校验。
        </p>
      </div>

      <div class="header-actions">
        <button
          class="create-button"
          type="button"
          @click="showCreateForm = !showCreateForm"
        >
          {{ showCreateForm ? '取消创建' : '新建客户' }}
        </button>

        <button class="refresh-button" type="button" @click="loadCustomers">
          刷新
        </button>
      </div>
    </header>

    <nav class="stage-filters" aria-label="客户阶段筛选">
      <RouterLink :to="{ name: 'customers' }" :class="{ active: !selectedStage }">全部客户</RouterLink>
      <RouterLink
        v-for="option in stageOptions"
        :key="option.value"
        :to="{ name: 'customers', query: { stage: option.value } }"
        :class="{ active: selectedStage === option.value }"
      >
        {{ option.label }}
      </RouterLink>
    </nav>

    <p v-if="!loading && !errorMessage" class="result-summary">
      {{ selectedStage ? stageLabels[selectedStage] : '全部' }}：{{ total }} 个客户
    </p>

    <CustomerCreateForm
      v-if="showCreateForm"
      @created="handleCustomerCreated"
    />

    <p v-if="loading" class="state-message">
      正在加载客户...
    </p>

    <p v-else-if="errorMessage" class="state-message error">
      {{ errorMessage }}
    </p>

    <section v-else class="customer-list">
      <p v-if="customers.length === 0" class="state-message">
        当前还没有客户数据。
      </p>

      <RouterLink
        v-for="customer in customers"
        :key="customer.id"
        :to="`/customers/${customer.id}`"
        class="customer-card"
      >
        <div>
          <h2>{{ customer.name }}</h2>
          <p class="phone">{{ customer.phone }}</p>
        </div>

        <div class="customer-meta">
          <span class="stage" :class="customer.stage">
            {{ stageLabels[customer.stage] }}
          </span>
          <span>
            下次跟进：{{ formatDate(customer.next_follow_up_at) }}
          </span>
        </div>
      </RouterLink>
    </section>
  </main>
</template>

<style scoped>
.customer-page {
  min-height: 100vh;
  padding: 38px 6vw 72px;
  color: #1f2937;
  background: radial-gradient(circle at 92% 0, rgb(37 99 235 / 10%), transparent 26rem), linear-gradient(180deg, #eef5ff 0, #f8fbff 340px);
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  max-width: 1080px;
  margin: 0 auto 24px;
  padding: 26px 28px;
  border: 1px solid rgb(255 255 255 / 82%);
  border-radius: 20px;
  background: rgb(255 255 255 / 76%);
  box-shadow: var(--shadow-sm);
}

.eyebrow {
  margin: 0 0 8px;
  color: #2563eb;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  font-size: clamp(32px, 5vw, 46px);
}

.description {
  max-width: 620px;
  margin-bottom: 0;
  color: #64748b;
  line-height: 1.65;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.stage-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-width: 960px;
  margin: 0 auto 14px;
}

.stage-filters a {
  padding: 8px 13px;
  border: 1px solid #d6e0ed;
  border-radius: 999px;
  color: #475569;
  background: rgb(255 255 255 / 82%);
  text-decoration: none;
}

.stage-filters a:hover,
.stage-filters a.active {
  border-color: #2563eb;
  color: #fff;
  background: #2563eb;
}

.result-summary {
  max-width: 960px;
  margin: 0 auto 14px;
  color: #64748b;
  font-size: 14px;
}

.create-button,
.refresh-button {
  padding: 10px 18px;
  border: 0;
  border-radius: 10px;
  color: white;
  cursor: pointer;
}

.create-button {
  background: linear-gradient(135deg, #2563eb, #4338ca);
}

.refresh-button {
  color: #1d4ed8;
  background: #dbeafe;
}

.customer-list {
  max-width: 960px;
  margin: 0 auto;
}

.customer-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 12px;
  padding: 20px 24px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: linear-gradient(145deg, #fff, #fbfdff);
  color: inherit;
  text-decoration: none;
  box-shadow: var(--shadow-sm);
  transition: transform .16s ease, box-shadow .16s ease, border-color .16s ease;
}

.customer-card:hover { transform: translateY(-2px); border-color: #93c5fd; box-shadow: var(--shadow-card); }

.customer-card h2 {
  margin: 0 0 6px;
  font-size: 20px;
}

.phone {
  margin: 0;
  color: #64748b;
}

.customer-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  color: #64748b;
  font-size: 14px;
}

.stage {
  padding: 4px 10px;
  border-radius: 999px;
  color: #1d4ed8;
  background: #dbeafe;
}

.stage.following_up { color: #9a5b00; background: #fff3cd; }
.stage.converted { color: #087443; background: #d9fbe7; }
.stage.lost { color: #7a4b62; background: #f6e8ef; }

.state-message {
  max-width: 960px;
  margin: 40px auto;
  color: #64748b;
}

.state-message.error {
  color: #dc2626;
}
@media (max-width: 650px) { .customer-page { padding: 22px 18px 48px; }.page-header { align-items: flex-start; flex-direction: column; padding: 22px; }.header-actions { width: 100%; }.header-actions button { flex: 1; }.customer-card { align-items: flex-start; flex-direction: column; }.customer-meta { align-items: flex-start; } }
</style>
