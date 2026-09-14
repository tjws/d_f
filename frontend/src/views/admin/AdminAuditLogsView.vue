<script setup lang="ts">
import { onMounted } from 'vue'
import AuditLogPanel from '../../components/admin/AuditLogPanel.vue'
import { useAdminConsole } from '../../composables/useAdminConsole'

const {
  auditLogs,
  auditTotal,
  auditPage,
  auditPageSize,
  errors,
  loadAuditLogs,
} = useAdminConsole()

onMounted(() => loadAuditLogs({ page: 1 }))
</script>

<template>
  <div class="admin-page">
    <header class="page-header">
      <p class="eyebrow">Governance</p>
      <h1>审计日志</h1>
      <p>此页面只读，审计记录不能通过前端编辑或删除。</p>
    </header>

    <AuditLogPanel
      :logs="auditLogs"
      :total="auditTotal"
      :page="auditPage"
      :page-size="auditPageSize"
      :error="errors.auditLogs"
      @search="loadAuditLogs"
    />
  </div>
</template>

<style scoped>
.admin-page {
  display: grid;
  gap: 20px;
}

.page-header {
  color: #1f2937;
}

.eyebrow {
  margin: 0 0 6px;
  color: #be123c;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

h1 {
  margin: 0;
}

.page-header p:last-child {
  color: #64748b;
}
</style>
