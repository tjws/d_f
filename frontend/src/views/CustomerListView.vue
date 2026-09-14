<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { listCustomers } from '../api/customers'
import type { Customer } from '../types/customer'
import CustomerCreateForm from '../components/customer/CustomerCreateForm.vue'

const customers = ref<Customer[]>([])
const loading = ref(false)
const errorMessage = ref('')
const showCreateForm = ref(false)

const stageLabels: Record<Customer['stage'], string> = {
  new: '新客户',
  following_up: '跟进中',
  converted: '已转化',
  lost: '已流失',
}

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
    })

    customers.value = response.items
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
</script>

<template>
  <main class="customer-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Customer Workspace</p>
        <h1>客户列表</h1>
        <p class="description">
          当前页面从 FastAPI customers API 读取客户数据。
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
          <span class="stage">
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
  padding: 48px 8vw;
  color: #1f2937;
  background: #f8fafc;
}

.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  max-width: 960px;
  margin: 0 auto 32px;
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
  font-size: 40px;
}

.description {
  color: #64748b;
}

.header-actions {
  display: flex;
  gap: 12px;
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
  background: #16a34a;
}

.refresh-button {
  background: #2563eb;
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
  margin-bottom: 16px;
  padding: 20px 24px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: white;
  color: inherit;
  text-decoration: none;
}

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

.state-message {
  max-width: 960px;
  margin: 40px auto;
  color: #64748b;
}

.state-message.error {
  color: #dc2626;
}
</style>
