<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { createSalesScript, listSalesScripts, updateSalesScript } from '../../api/salesScripts'
import { useAuth } from '../../composables/useAuth'
import type { SalesScript, SalesScriptCreate, SalesScriptStatus } from '../../types/salesScript'

const { currentRole } = useAuth()
const scripts = ref<SalesScript[]>([])
const loading = ref(true)
const error = ref('')
const saving = ref(false)
const editingId = ref<number | null>(null)
const form = ref<SalesScriptCreate>({ scene: 'reply', customer_stage: '', objection_type: '', title: '', content: '', tone: 'professional' })

function resetForm(): void {
  editingId.value = null
  form.value = { scene: 'reply', customer_stage: '', objection_type: '', title: '', content: '', tone: 'professional' }
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try { scripts.value = await listSalesScripts() } catch (reason) { error.value = reason instanceof Error ? reason.message : '话术库加载失败' } finally { loading.value = false }
}

function edit(script: SalesScript): void {
  editingId.value = script.id
  form.value = { scene: script.scene, customer_stage: script.customer_stage, objection_type: script.objection_type, title: script.title, content: script.content, tone: script.tone }
}

async function submit(): Promise<void> {
  if (!form.value.title.trim() || !form.value.content.trim()) { error.value = '标题和话术内容不能为空'; return }
  saving.value = true; error.value = ''
  try {
    if (editingId.value === null) await createSalesScript(form.value)
    else await updateSalesScript(editingId.value, form.value)
    resetForm(); await load()
  } catch (reason) { error.value = reason instanceof Error ? reason.message : '话术保存失败' } finally { saving.value = false }
}

async function transition(script: SalesScript, status: SalesScriptStatus): Promise<void> {
  error.value = ''
  try { await updateSalesScript(script.id, { status }); await load() } catch (reason) { error.value = reason instanceof Error ? reason.message : '状态更新失败' }
}

function nextAction(script: SalesScript): { label: string; status: SalesScriptStatus } | null {
  if (script.status === 'draft') return { label: '提交审核', status: 'pending_review' }
  if (script.status === 'pending_review') return { label: '发布', status: 'published' }
  if (script.status === 'published') return { label: '停用', status: 'disabled' }
  return { label: '重新启用', status: 'draft' }
}

onMounted(load)
</script>

<template>
  <div class="admin-page">
    <header class="page-header">
      <div><p class="eyebrow">Knowledge Operations</p><h1>销售话术库</h1><p>只有 published 版本会进入 AI 上下文；AI 仍只生成建议，不会自动发送。</p></div>
      <span class="role-badge">{{ currentRole || '未知角色' }}</span>
    </header>
    <p v-if="error" class="error">{{ error }}</p>
    <section class="editor panel">
      <h2>{{ editingId === null ? '新增话术' : '编辑话术' }}</h2>
      <div class="form-grid">
        <label>场景<select v-model="form.scene"><option value="reply">回复</option><option value="follow_up">跟进</option><option value="objection">异议处理</option></select></label>
        <label>客户阶段<input v-model="form.customer_stage" placeholder="new / following_up"></label>
        <label>异议类型<input v-model="form.objection_type" placeholder="价格、时间…"></label>
        <label>语气<input v-model="form.tone" placeholder="professional"></label>
        <label class="wide">标题<input v-model="form.title" placeholder="例如：试听邀约"></label>
        <label class="wide">内容<textarea v-model="form.content" rows="4" placeholder="输入供销售确认后使用的话术"></textarea></label>
      </div>
      <div class="form-actions"><button :disabled="saving || currentRole === 'sales'" @click="submit">{{ saving ? '保存中…' : '保存草稿' }}</button><button v-if="editingId !== null" class="secondary" @click="resetForm">取消编辑</button></div>
    </section>
    <p v-if="loading">加载中…</p>
    <p v-else-if="!scripts.length" class="empty">暂无话术，先创建一条草稿。</p>
    <section v-else class="script-list">
      <article v-for="script in scripts" :key="script.id" class="script-card">
        <div class="script-head"><div><h2>{{ script.title }}</h2><p>{{ script.scene }} · {{ script.customer_stage || '未限定阶段' }} · v{{ script.version }}</p></div><span class="status" :data-status="script.status">{{ script.status }}</span></div>
        <p class="content">{{ script.content }}</p>
        <div class="script-actions"><button class="secondary" :disabled="currentRole === 'sales'" @click="edit(script)">编辑</button><button v-if="nextAction(script)" :disabled="currentRole === 'sales'" @click="transition(script, nextAction(script)!.status)">{{ nextAction(script)!.label }}</button></div>
      </article>
    </section>
  </div>
</template>

<style scoped>
.admin-page { display: grid; gap: 20px; }
.page-header { display: flex; justify-content: space-between; gap: 16px; }
.page-header h1 { margin: 0; }.eyebrow { margin: 0 0 6px; color: #2563eb; font-size: 12px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }.page-header p:last-child { color: #64748b; }
.role-badge, .status { align-self: flex-start; padding: 6px 10px; border-radius: 999px; color: #1d4ed8; background: #dbeafe; font-size: 12px; }.status[data-status="published"] { color: #166534; background: #dcfce7; }.status[data-status="disabled"] { color: #64748b; background: #e2e8f0; }
.panel, .script-card { padding: 20px; border: 1px solid #dbe5f3; border-radius: 16px; background: white; box-shadow: 0 8px 22px rgb(30 64 175 / 5%); }.panel h2 { margin-top: 0; }.form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }label { display: grid; gap: 6px; color: #475569; font-size: 13px; }.wide { grid-column: 1 / -1; }input, select, textarea { box-sizing: border-box; width: 100%; padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; font: inherit; }textarea { resize: vertical; }.form-actions, .script-actions { display: flex; gap: 8px; margin-top: 14px; }button { padding: 9px 14px; border: 0; border-radius: 8px; color: white; background: #2563eb; cursor: pointer; }button:disabled { cursor: not-allowed; opacity: .5; }.secondary { color: #1e40af; background: #eff6ff; }.script-list { display: grid; gap: 14px; }.script-head { display: flex; justify-content: space-between; gap: 12px; }.script-head h2 { margin: 0; font-size: 18px; }.script-head p, .content, .empty { color: #64748b; }.content { white-space: pre-wrap; line-height: 1.6; }.error { color: #b91c1c; }
@media (max-width: 700px) { .form-grid { grid-template-columns: 1fr; }.wide { grid-column: auto; }.page-header { flex-direction: column; } }
</style>
