<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { listSystemSettings, updateSystemSetting } from '../../api/systemSettings'
import { useAuth } from '../../composables/useAuth'
import type { SystemSetting } from '../../types/systemSetting'

const { currentRole } = useAuth()
const settings = ref<SystemSetting[]>([])
const values = ref<Record<string, number | boolean>>({})
const loading = ref(true)
const savingKey = ref<string | null>(null)
const error = ref('')
const message = ref('')
const canEdit = computed(() => currentRole.value === 'admin')
const visibleSettings = computed(() => settings.value.filter((item) => item.key !== 'ai_rollout_mode'))

const labels: Record<string, string> = {
  comprehensive_agent_enabled: 'Comprehensive Agent global switch',
  ai_daily_bailian_request_limit: '每日百炼调用上限',
  knowledge_max_results: '知识库最多返回条数',
  default_follow_up_days: '默认跟进天数',
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    settings.value = await listSystemSettings()
    values.value = Object.fromEntries(
      settings.value.map((item) => [item.key, item.value]).filter((item): item is [string, number | boolean] => typeof item[1] === 'number' || typeof item[1] === 'boolean'),
    )
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '系统设置加载失败'
  } finally {
    loading.value = false
  }
}

async function save(setting: SystemSetting): Promise<void> {
  if (!canEdit.value) return
  savingKey.value = setting.key
  error.value = ''
  message.value = ''
  try {
    const updated = await updateSystemSetting(setting.key, values.value[setting.key])
    settings.value = settings.value.map((item) => item.key === updated.key ? updated : item)
    message.value = '设置已保存'
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '设置保存失败'
  } finally {
    savingKey.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="admin-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Operations</p>
        <h1>系统设置</h1>
        <p>管理非敏感运营参数。AI provider 与 API Key 仍由环境变量控制，不写入数据库。</p>
      </div>
    </header>
    <p v-if="loading">加载中…</p>
    <p v-else-if="error" class="error">{{ error }}</p>
    <p v-else-if="!settings.length" class="empty">暂无可管理的设置。</p>
    <section v-else class="settings-grid">
      <article v-for="setting in visibleSettings" :key="setting.key" class="setting-card">
        <div>
          <h2>{{ labels[setting.key] || setting.key }}</h2>
          <p>{{ setting.description || '暂无说明' }}</p>
          <code>{{ setting.key }}</code>
        </div>
        <div class="setting-actions">
          <label v-if="setting.key === 'comprehensive_agent_enabled'" class="toggle">
            <input v-model="values[setting.key]" type="checkbox" :disabled="!canEdit || savingKey === setting.key">
            <span>{{ values[setting.key] ? 'Enabled' : 'Disabled' }}</span>
          </label>
          <input v-else v-model.number="values[setting.key]" type="number" :disabled="!canEdit || savingKey === setting.key">
          <button :disabled="!canEdit || savingKey === setting.key" @click="save(setting)">
            {{ savingKey === setting.key ? '保存中…' : '保存' }}
          </button>
        </div>
      </article>
    </section>
    <p v-if="!canEdit && !loading" class="hint">当前角色只能查看设置；只有 admin 可以修改。</p>
    <p v-if="message" class="success">{{ message }}</p>
  </div>
</template>

<style scoped>
.admin-page { display: grid; gap: 20px; }
.page-header h1 { margin: 0; }
.eyebrow { margin: 0 0 6px; color: #2563eb; font-size: 12px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
.page-header p:last-child, .empty, .hint { color: #64748b; }
.settings-grid { display: grid; gap: 14px; }
.setting-card { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 20px; border: 1px solid #dbe5f3; border-radius: 16px; background: white; box-shadow: 0 8px 22px rgb(30 64 175 / 5%); }
.setting-card h2 { margin: 0; font-size: 18px; }
.setting-card p { margin: 6px 0; color: #64748b; }
code { color: #64748b; font-size: 12px; }
.setting-actions { display: flex; align-items: center; gap: 8px; }
input { width: 100px; padding: 9px 10px; border: 1px solid #cbd5e1; border-radius: 8px; font: inherit; }
.toggle { display: inline-flex; align-items: center; gap: 8px; color: #334155; font-size: 13px; }
.toggle input { width: 18px; height: 18px; }
button { padding: 9px 14px; border: 0; border-radius: 8px; color: white; background: #2563eb; cursor: pointer; }
button:disabled { cursor: not-allowed; opacity: .5; }
.error { color: #b91c1c; }
.success { color: #15803d; }
@media (max-width: 700px) { .setting-card { align-items: flex-start; flex-direction: column; } }
</style>
