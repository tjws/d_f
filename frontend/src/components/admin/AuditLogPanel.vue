<script setup lang="ts">
import { computed, ref } from 'vue'
import type { AuditLog } from '../../types/auditLog'

const props = defineProps<{
  logs: AuditLog[]
  total: number
  page: number
  pageSize: number
  error?: string
}>()

const emit = defineEmits<{
  search: [query: {
    page: number
    page_size: number
    action?: string
    target_type?: string
    target_id?: string
  }]
}>()

const action = ref('')
const targetType = ref('')
const targetId = ref('')

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

function search(page = 1): void {
  emit('search', {
    page,
    page_size: props.pageSize,
    action: action.value || undefined,
    target_type: targetType.value || undefined,
    target_id: targetId.value || undefined,
  })
}
</script>

<template>
  <section class="panel">
    <header class="panel-header">
      <div>
        <p class="eyebrow">Audit Logs</p>
        <h2>审计日志</h2>
      </div>
      <span>{{ props.total }} records</span>
    </header>

    <form class="filters" @submit.prevent="search(1)">
      <input v-model="action" placeholder="action" />
      <input v-model="targetType" placeholder="target_type" />
      <input v-model="targetId" placeholder="target_id" />
      <button type="submit">查询</button>
    </form>

    <p v-if="props.error" class="error">{{ props.error }}</p>

    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>时间</th>
            <th>操作者</th>
            <th>action</th>
            <th>目标</th>
            <th>结果</th>
            <th>详情</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in props.logs" :key="log.id">
            <td>{{ log.created_at }}</td>
            <td>{{ log.actor_username_snapshot || 'system' }}</td>
            <td>{{ log.action }}</td>
            <td>{{ log.target_type }}#{{ log.target_id }}</td>
            <td>{{ log.result }}</td>
            <td>
              <details>
                <summary>查看</summary>
                <pre>{{ JSON.stringify(log.detail_json, null, 2) }}</pre>
              </details>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="pagination">
      <button type="button" :disabled="props.page <= 1" @click="search(props.page - 1)">
        上一页
      </button>
      <span>{{ props.page }} / {{ totalPages }}</span>
      <button type="button" :disabled="props.page >= totalPages" @click="search(props.page + 1)">
        下一页
      </button>
    </div>
  </section>
</template>

<style scoped>
.panel {
  padding: 24px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: white;
}

.panel-header,
.pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.eyebrow {
  margin: 0 0 6px;
  color: #be123c;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

h2 {
  margin: 0 0 18px;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 18px;
}

input {
  min-width: 160px;
  padding: 9px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
}

button {
  padding: 8px 12px;
  border: 0;
  border-radius: 8px;
  color: white;
  background: #be123c;
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.table-wrapper {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  padding: 11px;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
  white-space: nowrap;
}

pre {
  max-width: 260px;
  white-space: pre-wrap;
}

.pagination {
  margin-top: 18px;
}

.error {
  color: #dc2626;
}
</style>
