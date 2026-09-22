<script setup lang="ts">
import { computed } from 'vue'
import { useAuth } from '../../composables/useAuth'

const { currentRole } = useAuth()
const canViewAIDashboard = computed(() => currentRole.value === 'admin' || currentRole.value === 'manager')
</script>

<template>
  <aside class="navigation">
    <div class="navigation-head"><div><p class="eyebrow">Admin Console</p><h1>管理后台</h1></div><RouterLink to="/customers" class="back-workspace">返回工作台</RouterLink></div>
    <nav aria-label="管理后台导航">
      <section class="nav-group primary"><p>先看全局</p><RouterLink to="/admin/overview">管理总览</RouterLink><RouterLink v-if="canViewAIDashboard" to="/admin/business-dashboard">经营看板</RouterLink><RouterLink v-if="canViewAIDashboard" to="/admin/churn-risks">流失风险</RouterLink></section>
      <details class="nav-group"><summary>团队与数据</summary><RouterLink to="/admin/users">用户与组织</RouterLink><RouterLink v-if="canViewAIDashboard" to="/admin/tags">标签管理</RouterLink><RouterLink v-if="canViewAIDashboard" to="/admin/operations">订单与工单</RouterLink><RouterLink v-if="canViewAIDashboard" to="/admin/permissions">权限矩阵</RouterLink><RouterLink v-if="currentRole === 'admin'" to="/admin/data-export">数据导出</RouterLink><RouterLink to="/admin/audit-logs">审计日志</RouterLink></details>
      <details v-if="canViewAIDashboard" class="nav-group"><summary>AI 与知识</summary><RouterLink to="/admin/ai-dashboard">AI 采用率</RouterLink><RouterLink to="/admin/ai-workflow-runs">运行历史</RouterLink><RouterLink to="/admin/sales-scripts">销售话术库</RouterLink><RouterLink to="/admin/knowledge">知识库</RouterLink><RouterLink to="/admin/rag-evaluation">RAG 评测</RouterLink><RouterLink to="/admin/ai-rollout">灰度发布</RouterLink></details>
      <details v-if="canViewAIDashboard" class="nav-group"><summary>系统运维</summary><RouterLink to="/admin/system-status">运行状态</RouterLink><RouterLink to="/admin/system-settings">系统设置</RouterLink></details>
    </nav>
  </aside>
</template>

<style scoped>
.navigation {
  padding: 20px max(24px, 6vw) 18px;
  color: white;
  background: linear-gradient(110deg, #0f172a, #172554 48%, #1e3a8a);
  box-shadow: 0 8px 24px rgb(15 23 42 / 18%);
}
.navigation-head { display: flex; align-items: center; justify-content: space-between; gap: 18px; max-width: 1180px; margin: 0 auto 15px; }
.eyebrow {
  margin: 0 0 6px;
  color: #93c5fd;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

h1 { margin: 0; color: white; font-size: 24px; }.back-workspace { padding: 7px 10px; border: 1px solid rgb(147 197 253 / 25%); border-radius: 9px; color: #dbeafe; text-decoration: none; font-size: 12px; }.back-workspace:hover { background: rgb(255 255 255 / 8%); }

nav {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  max-width: 1180px;
  margin: 0 auto;
}
.nav-group { display: flex; flex-wrap: wrap; gap: 7px; align-items: center; }.nav-group p { width: 100%; margin: 0 0 1px; color: #93c5fd; font-size: 10px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }.nav-group:not(.primary) { display: block; min-width: 120px; }.nav-group summary { color: #bfdbfe; font-size: 12px; font-weight: 800; cursor: pointer; list-style: none; }.nav-group summary::after { margin-left: 5px; content: '⌄'; }.nav-group[open] summary { margin-bottom: 7px; }.nav-group[open] summary::after { content: '⌃'; }.nav-group:not(.primary) a { display: inline-block; }
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
@media (max-width: 700px) { .navigation { padding: 16px 18px; }.navigation-head { margin-bottom: 16px; }.nav-group { width: 100%; }.nav-group a { font-size: 12px; }.back-workspace { white-space: nowrap; } }
</style>
