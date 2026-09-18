<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { listUsers, type AdminUser } from '../../api/users'
import {
  addAIRolloutMember,
  generateAIRolloutReport,
  getAIRolloutConfig,
  listAIRolloutMembers,
  listAIRolloutReports,
  removeAIRolloutMember,
  updateAIRolloutMode,
  type AIRolloutConfig,
  type AIRolloutMember,
  type AIRolloutMode,
  type AIRolloutReport,
  type AIRolloutSegment,
} from '../../api/aiRollout'
import { useAuth } from '../../composables/useAuth'

const { currentRole } = useAuth()
const canEdit = computed(() => currentRole.value === 'admin')
const config = ref<AIRolloutConfig | null>(null)
const members = ref<AIRolloutMember[]>([])
const reports = ref<AIRolloutReport[]>([])
const users = ref<AdminUser[]>([])
const mode = ref<AIRolloutMode>('all')
const selectedUserId = ref<number | null>(null)
const segment = ref<AIRolloutSegment>('unclassified')
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const notice = ref('')

const availableUsers = computed(() => {
  const activeIds = new Set(members.value.filter((item) => item.status === 'active').map((item) => item.user_id))
  return users.value.filter((item) => item.is_active && !activeIds.has(item.id))
})

async function load(): Promise<void> {
  loading.value = true; error.value = ''
  try {
    const [loadedConfig, loadedMembers, loadedReports, loadedUsers] = await Promise.all([
      getAIRolloutConfig(), listAIRolloutMembers(), listAIRolloutReports(), listUsers(),
    ])
    config.value = loadedConfig; mode.value = loadedConfig.mode; members.value = loadedMembers; reports.value = loadedReports; users.value = loadedUsers
  } catch (reason) { error.value = reason instanceof Error ? reason.message : '灰度配置加载失败' } finally { loading.value = false }
}

async function saveMode(): Promise<void> {
  if (!canEdit.value) return
  saving.value = true; error.value = ''; notice.value = ''
  try { config.value = await updateAIRolloutMode(mode.value); notice.value = mode.value === 'pilot' ? '已切换到灰度模式，只有名单成员可运行综合 Agent。' : '已恢复全量模式。' } catch (reason) { error.value = reason instanceof Error ? reason.message : '灰度模式保存失败' } finally { saving.value = false }
}

async function addMember(): Promise<void> {
  if (!canEdit.value || selectedUserId.value === null) return
  saving.value = true; error.value = ''; notice.value = ''
  try { await addAIRolloutMember(selectedUserId.value, segment.value); selectedUserId.value = null; await load(); notice.value = '灰度成员已加入。' } catch (reason) { error.value = reason instanceof Error ? reason.message : '灰度成员添加失败' } finally { saving.value = false }
}

async function removeMember(userId: number): Promise<void> {
  if (!canEdit.value) return
  saving.value = true; error.value = ''; notice.value = ''
  try { await removeAIRolloutMember(userId); await load(); notice.value = '灰度成员已移出。' } catch (reason) { error.value = reason instanceof Error ? reason.message : '灰度成员移除失败' } finally { saving.value = false }
}

async function generateReport(): Promise<void> {
  if (!canEdit.value) return
  saving.value = true; error.value = ''; notice.value = ''
  try { await generateAIRolloutReport(); await load(); notice.value = '今日灰度日报已生成或更新。' } catch (reason) { error.value = reason instanceof Error ? reason.message : '灰度日报生成失败' } finally { saving.value = false }
}

function metric(report: AIRolloutReport, key: string): string {
  const value = report.metrics[key]
  if (typeof value === 'number') return key.includes('rate') || key === 'adoption_rate' ? `${(value * 100).toFixed(1)}%` : String(value)
  return value == null ? '-' : String(value)
}

onMounted(load)
</script>

<template>
  <div class="admin-page">
    <header class="page-header"><div><p class="eyebrow">AI Release Control</p><h1>AI 灰度发布</h1><p>先用 30 人试运行，再依据每日指标决定是否恢复全量。后端门禁优先于前端入口。</p></div><span class="role-badge">{{ currentRole || '未知角色' }}</span></header>
    <p v-if="error" class="error">{{ error }}</p><p v-if="notice" class="notice">{{ notice }}</p><p v-if="loading">加载中…</p>
    <template v-else>
      <section class="panel config-panel"><div><h2>发布模式</h2><p>当前 active 灰度成员 {{ config?.active_member_count || 0 }} / {{ config?.max_member_count || 30 }}。</p></div><div class="config-actions"><select v-model="mode" :disabled="!canEdit || saving"><option value="all">all · 全量</option><option value="pilot">pilot · 仅灰度名单</option></select><button :disabled="!canEdit || saving" @click="saveMode">保存模式</button><button class="secondary" :disabled="!canEdit || saving" @click="generateReport">生成今日日报</button></div></section>
      <section class="panel"><div class="panel-head"><div><h2>灰度成员</h2><p>建议分为新人和老顾问两组；最多 30 名 active 用户。</p></div><div v-if="canEdit" class="add-form"><select v-model="selectedUserId"><option :value="null">选择用户</option><option v-for="user in availableUsers" :key="user.id" :value="user.id">{{ user.full_name || user.username }}（{{ user.role }}）</option></select><select v-model="segment"><option value="new">新人</option><option value="experienced">老顾问</option><option value="unclassified">未分类</option></select><button :disabled="saving || selectedUserId === null" @click="addMember">加入名单</button></div></div><p v-if="!members.length" class="empty">还没有灰度成员。</p><table v-else><thead><tr><th>用户</th><th>角色</th><th>分组</th><th>状态</th><th>开始时间</th><th></th></tr></thead><tbody><tr v-for="item in members" :key="item.id"><td>{{ item.full_name || item.username }}</td><td>{{ item.role }}</td><td>{{ item.segment }}</td><td>{{ item.status }}</td><td>{{ new Date(item.started_at).toLocaleString() }}</td><td><button v-if="canEdit && item.status === 'active'" class="danger" :disabled="saving" @click="removeMember(item.user_id)">移出</button></td></tr></tbody></table></section>
      <section class="panel"><div class="panel-head"><div><h2>灰度日报</h2><p>日报复用 AI 看板指标，按 UTC 日期保存快照。</p></div></div><p v-if="!reports.length" class="empty">尚未生成日报。</p><table v-else><thead><tr><th>日期</th><th>活跃成员</th><th>采用率</th><th>RAG fallback</th><th>Agent 失败</th><th>平均耗时</th></tr></thead><tbody><tr v-for="report in reports" :key="report.id"><td>{{ report.report_date }}</td><td>{{ metric(report, 'active_member_count') }}</td><td>{{ metric(report, 'adoption_rate') }}</td><td>{{ metric(report, 'rag_fallback_rate') }}</td><td>{{ metric(report, 'agent_reasoning_failures') }}</td><td>{{ metric(report, 'avg_task_duration_ms') }} ms</td></tr></tbody></table></section>
    </template>
  </div>
</template>

<style scoped>
.admin-page { display: grid; gap: 20px; }.page-header { display: flex; justify-content: space-between; gap: 16px; }.page-header h1 { margin: 0; }.eyebrow { margin: 0 0 6px; color: #be123c; font-size: 12px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }.page-header p:last-child, .panel p, .empty { color: #64748b; }.role-badge { padding: 6px 10px; border-radius: 999px; color: #1d4ed8; background: #dbeafe; font-size: 12px; }.panel { padding: 20px; border: 1px solid #dbe5f3; border-radius: 16px; background: #fff; box-shadow: 0 8px 22px rgb(30 64 175 / 5%); }.config-panel, .panel-head { display: flex; justify-content: space-between; gap: 16px; }.panel h2 { margin: 0; }.config-actions, .add-form { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }.config-actions select, .add-form select { padding: 9px; border: 1px solid #cbd5e1; border-radius: 8px; background: #fff; font: inherit; }button { padding: 9px 13px; border: 0; border-radius: 8px; color: #fff; background: #2563eb; cursor: pointer; }button:disabled { opacity: .5; cursor: not-allowed; }.secondary { color: #1e40af; background: #eff6ff; }.danger { color: #b91c1c; background: #fee2e2; }.error { color: #b91c1c !important; }.notice { color: #15803d !important; }table { width: 100%; border-collapse: collapse; margin-top: 14px; }th, td { padding: 10px 8px; text-align: left; border-bottom: 1px solid #e2e8f0; }th { color: #475569; font-size: 12px; }@media (max-width: 800px) { .page-header, .config-panel, .panel-head { flex-direction: column; }.config-actions, .add-form { align-items: stretch; flex-direction: column; } }
</style>
