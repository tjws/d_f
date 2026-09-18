<script setup lang="ts">
import { computed } from 'vue'
import { useAuth } from '../../composables/useAuth'

const { currentRole } = useAuth()
const canViewAIDashboard = computed(() => currentRole.value === 'admin' || currentRole.value === 'manager')
</script>

<template>
  <aside class="navigation">
    <p class="eyebrow">Admin Console</p>
    <h1>管理后台</h1>
    <nav>
      <RouterLink to="/admin/overview">管理总览</RouterLink>
      <RouterLink to="/admin/users">用户与组织</RouterLink>
      <RouterLink to="/admin/audit-logs">审计日志</RouterLink>
      <RouterLink v-if="canViewAIDashboard" to="/admin/ai-dashboard">AI 采用率</RouterLink>
      <RouterLink v-if="canViewAIDashboard" to="/admin/business-dashboard">业务经营看板</RouterLink>
      <RouterLink v-if="canViewAIDashboard" to="/admin/tags">标签管理</RouterLink>
      <RouterLink v-if="canViewAIDashboard" to="/admin/operations">订单与工单</RouterLink>
      <RouterLink v-if="canViewAIDashboard" to="/admin/permissions">权限矩阵</RouterLink>
      <RouterLink v-if="currentRole === 'admin'" to="/admin/data-export">数据导出</RouterLink>
      <RouterLink v-if="canViewAIDashboard" to="/admin/ai-workflow-runs">AI 运行历史</RouterLink>
      <RouterLink v-if="canViewAIDashboard" to="/admin/system-settings">系统设置</RouterLink>
      <RouterLink v-if="canViewAIDashboard" to="/admin/system-status">运行状态</RouterLink>
      <RouterLink v-if="canViewAIDashboard" to="/admin/sales-scripts">销售话术库</RouterLink>
      <RouterLink v-if="canViewAIDashboard" to="/admin/knowledge">知识库</RouterLink>
      <RouterLink v-if="canViewAIDashboard" to="/admin/rag-evaluation">RAG 评测闭环</RouterLink>
      <RouterLink v-if="canViewAIDashboard" to="/admin/ai-rollout">AI 灰度发布</RouterLink>
      <RouterLink to="/customers">返回客户工作台</RouterLink>
    </nav>
  </aside>
</template>

<style scoped>
.navigation {
  padding: 22px max(24px, 6vw);
  color: white;
  background: linear-gradient(110deg, #0f172a, #1e3a8a);
  box-shadow: 0 8px 24px rgb(15 23 42 / 18%);
}

.eyebrow {
  margin: 0 0 6px;
  color: #93c5fd;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

h1 {
  margin: 0 0 20px;
  font-size: 24px;
}

nav {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

a {
  padding: 8px 12px;
  border-radius: 8px;
  color: #cbd5e1;
  text-decoration: none;
  border: 1px solid transparent;
  transition: background .15s ease, border-color .15s ease;
}

a:hover { border-color: rgb(147 197 253 / 35%); background: rgb(255 255 255 / 9%); }

a.router-link-active {
  color: white;
  background: #2563eb;
}
</style>
