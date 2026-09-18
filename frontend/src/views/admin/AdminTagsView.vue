<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { createAdminTag, listAdminTags, updateAdminTag, type AdminTag } from '../../api/adminTags'
import { useAuth } from '../../composables/useAuth'

const { currentRole } = useAuth()
const tags = ref<AdminTag[]>([])
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const showForm = ref(false)
const editingId = ref<number | null>(null)
const form = ref({ key: '', name: '', category: '', description: '', color: '#2563eb' })
const canEdit = computed(() => currentRole.value === 'admin')

function resetForm(): void {
  form.value = { key: '', name: '', category: '', description: '', color: '#2563eb' }
  editingId.value = null
  showForm.value = false
}

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    tags.value = await listAdminTags()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '标签目录加载失败'
  } finally {
    loading.value = false
  }
}

function edit(tag: AdminTag): void {
  editingId.value = tag.id
  form.value = { key: tag.key, name: tag.name, category: tag.category, description: tag.description || '', color: tag.color || '#2563eb' }
  showForm.value = true
}

async function save(): Promise<void> {
  if (!canEdit.value || saving.value) return
  saving.value = true
  error.value = ''
  try {
    if (editingId.value === null) {
      await createAdminTag({ ...form.value, description: form.value.description || null, color: form.value.color || null })
    } else {
      await updateAdminTag(editingId.value, { ...form.value, description: form.value.description || null, color: form.value.color || null })
    }
    resetForm()
    await load()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '标签保存失败'
  } finally {
    saving.value = false
  }
}

async function toggleStatus(tag: AdminTag): Promise<void> {
  if (!canEdit.value || saving.value) return
  saving.value = true
  error.value = ''
  try {
    await updateAdminTag(tag.id, { status: tag.status === 'active' ? 'inactive' : 'active' })
    await load()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '标签状态更新失败'
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="admin-page">
    <header class="page-header">
      <div><p class="eyebrow">Tag Governance</p><h1>标签管理</h1><p>维护统一标签目录，并查看 AI 建议、人工确认和客户覆盖统计。</p></div>
      <button v-if="canEdit" type="button" :disabled="saving" @click="showForm = !showForm; editingId = null">{{ showForm ? '取消' : '新建标签' }}</button>
    </header>

    <p v-if="error" class="error">{{ error }}</p>
    <form v-if="showForm && canEdit" class="panel form-grid" @submit.prevent="save">
      <h2>{{ editingId === null ? '新建标签' : '编辑标签' }}</h2>
      <label>Key<input v-model="form.key" required pattern="[a-z0-9][a-z0-9_-]*" maxlength="80" placeholder="high_intent"></label>
      <label>名称<input v-model="form.name" required maxlength="50" placeholder="高意向"></label>
      <label>分类<input v-model="form.category" required maxlength="50" placeholder="意向度"></label>
      <label>颜色<input v-model="form.color" maxlength="20" placeholder="#2563eb"></label>
      <label class="wide">说明<textarea v-model="form.description" maxlength="500" rows="2"></textarea></label>
      <div class="form-actions wide"><button type="submit" :disabled="saving">{{ saving ? '保存中…' : '保存标签' }}</button><button type="button" class="secondary" @click="resetForm">取消</button></div>
    </form>

    <p v-if="loading" class="muted">正在加载标签目录…</p>
    <section v-else class="panel">
      <p v-if="!tags.length" class="muted">还没有标签目录。管理员可以先创建一个标签。</p>
      <div v-else class="table-wrap">
        <table><thead><tr><th>标签</th><th>分类</th><th>状态</th><th>客户数</th><th>建议</th><th>确认</th><th>拒绝</th><th v-if="canEdit">操作</th></tr></thead>
          <tbody><tr v-for="tag in tags" :key="tag.id"><td><strong>{{ tag.name }}</strong><small>{{ tag.key }}</small></td><td>{{ tag.category }}</td><td><span class="status" :data-status="tag.status">{{ tag.status === 'active' ? '启用' : '停用' }}</span></td><td>{{ tag.customer_count }}</td><td>{{ tag.suggested_count }}</td><td>{{ tag.confirmed_count }}</td><td>{{ tag.rejected_count }}</td><td v-if="canEdit" class="actions"><button type="button" class="link-button" @click="edit(tag)">编辑</button><button type="button" class="link-button" @click="toggleStatus(tag)">{{ tag.status === 'active' ? '停用' : '启用' }}</button></td></tr></tbody>
        </table>
      </div>
    </section>
    <p v-if="!canEdit" class="muted">当前为 manager，只读查看标签统计；只有 admin 可以修改标签目录。</p>
  </div>
</template>

<style scoped>
.admin-page { display: grid; gap: 20px; }.page-header { display: flex; align-items: end; justify-content: space-between; gap: 20px; }.page-header h1 { margin: 0; }.page-header p:last-child, .muted { color: #64748b; }.eyebrow { margin: 0 0 6px; color: #d97706; font-size: 12px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }button { padding: 9px 14px; border: 0; border-radius: 8px; color: #fff; background: #2563eb; cursor: pointer; }button:disabled { cursor: wait; opacity: .6; }.error { color: #b91c1c; }.panel { padding: 20px; border: 1px solid #dbe5f3; border-radius: 16px; background: #fff; box-shadow: 0 8px 22px rgb(30 64 175 / 5%); }.form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }.form-grid h2 { grid-column: 1 / -1; margin: 0; }.form-grid label { display: grid; gap: 5px; color: #475569; font-size: 13px; font-weight: 700; }.form-grid input, .form-grid textarea { box-sizing: border-box; width: 100%; padding: 8px; border: 1px solid #cbd5e1; border-radius: 8px; font: inherit; }.wide { grid-column: 1 / -1; }.form-actions { display: flex; gap: 8px; }.secondary { color: #475569; background: #e2e8f0; }.table-wrap { overflow-x: auto; }table { width: 100%; border-collapse: collapse; }th, td { padding: 11px 8px; text-align: left; border-bottom: 1px solid #e2e8f0; white-space: nowrap; }th { color: #475569; font-size: 12px; }td small { display: block; margin-top: 3px; color: #94a3b8; font-size: 12px; }.status { padding: 4px 8px; border-radius: 999px; color: #166534; background: #dcfce7; font-size: 12px; }.status[data-status="inactive"] { color: #64748b; background: #e2e8f0; }.actions { display: flex; gap: 8px; }.link-button { padding: 0; color: #2563eb; background: transparent; font-size: 13px; }.link-button:hover { text-decoration: underline; }@media (max-width: 650px) { .page-header { align-items: flex-start; flex-direction: column; }.form-grid { grid-template-columns: 1fr; } }
</style>
