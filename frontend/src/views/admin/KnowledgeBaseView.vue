<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { createKnowledgeDocument, evaluateKnowledge, listKnowledgeDocuments, reindexKnowledgeVectors, updateKnowledgeDocument } from '../../api/knowledge'
import { useAuth } from '../../composables/useAuth'
import type { KnowledgeDocument, KnowledgeDocumentCreate, KnowledgeStatus } from '../../api/knowledge'

const { currentRole } = useAuth()
const documents = ref<KnowledgeDocument[]>([])
const loading = ref(true)
const saving = ref(false)
const reindexing = ref(false)
const error = ref('')
const notice = ref('')
const evaluation = ref<Awaited<ReturnType<typeof evaluateKnowledge>> | null>(null)
const evaluating = ref(false)
const editingId = ref<number | null>(null)
const form = ref<KnowledgeDocumentCreate>({ slug: '', title: '', category: '课程', source: 'admin', content: '' })

function resetForm(): void {
  editingId.value = null
  form.value = { slug: '', title: '', category: '课程', source: 'admin', content: '' }
}

async function load(): Promise<void> {
  loading.value = true; error.value = ''; notice.value = ''
  try { documents.value = await listKnowledgeDocuments() } catch (reason) { error.value = reason instanceof Error ? reason.message : '知识库加载失败' } finally { loading.value = false }
}

function edit(document: KnowledgeDocument): void {
  editingId.value = document.id
  form.value = { slug: document.slug, title: document.title, category: document.category, source: document.source, content: document.chunks.map((chunk) => chunk.content).join('\n\n') }
}

async function submit(): Promise<void> {
  if (!form.value.slug.trim() || !form.value.title.trim() || form.value.content.trim().length < 10) { error.value = '标识、标题和至少 10 个字符的正文不能为空'; return }
  saving.value = true; error.value = ''
  try {
    if (editingId.value === null) await createKnowledgeDocument(form.value)
    else await updateKnowledgeDocument(editingId.value, { title: form.value.title, category: form.value.category, content: form.value.content })
    resetForm(); await load()
  } catch (reason) { error.value = reason instanceof Error ? reason.message : '知识文档保存失败' } finally { saving.value = false }
}

async function transition(document: KnowledgeDocument, status: KnowledgeStatus): Promise<void> {
  error.value = ''
  try { await updateKnowledgeDocument(document.id, { status }); await load() } catch (reason) { error.value = reason instanceof Error ? reason.message : '文档状态更新失败' }
}

async function reindex(): Promise<void> {
  reindexing.value = true; error.value = ''; notice.value = ''
  try {
    const result = await reindexKnowledgeVectors()
    notice.value = `向量索引完成：${result.indexed} 个分片（${result.provider}）`
  } catch (reason) { error.value = reason instanceof Error ? reason.message : '向量索引失败' } finally { reindexing.value = false }
}

async function runEvaluation(): Promise<void> {
  evaluating.value = true; error.value = ''; notice.value = ''
  try { evaluation.value = await evaluateKnowledge(3); notice.value = 'RAG 评测完成（只读检索，未调用生成模型）' } catch (reason) { error.value = reason instanceof Error ? reason.message : 'RAG 评测失败' } finally { evaluating.value = false }
}

function action(document: KnowledgeDocument): { label: string; status: KnowledgeStatus } {
  if (document.status === 'draft') return { label: '发布', status: 'published' }
  if (document.status === 'published') return { label: '停用', status: 'disabled' }
  return { label: '重新启用为草稿', status: 'draft' }
}

function indexStatusLabel(status: KnowledgeDocument['vector_index_status']): string {
  return ({ pending: '待索引', indexing: '索引中', ready: '已就绪', failed: '失败', disabled: '未启用' })[status]
    ?? status
}

onMounted(load)
</script>

<template>
  <div class="admin-page">
    <header class="page-header">
      <div><p class="eyebrow">RAG Operations</p><h1>知识库</h1><p>文档先保存为草稿，发布后才会被本地 RAG 和 AI 工作流检索。</p></div>
      <span class="role-badge">{{ currentRole || '未知角色' }}</span>
    </header>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>
    <section class="panel">
      <h2>{{ editingId === null ? '新增知识文档' : '编辑知识文档' }}</h2>
      <div class="form-grid">
        <label>唯一标识<input v-model="form.slug" :disabled="editingId !== null" placeholder="例如：trial_math_v1"></label>
        <label>标题<input v-model="form.title" placeholder="例如：初中数学试听流程"></label>
        <label>分类<input v-model="form.category" placeholder="课程 / 沟通 / 政策"></label>
        <label>来源<input v-model="form.source" placeholder="admin"></label>
        <label class="wide">正文<textarea v-model="form.content" rows="6" placeholder="每个段落之间空一行，系统会自动切分检索片段"></textarea></label>
      </div>
      <div class="actions"><button :disabled="saving || currentRole === 'sales'" @click="submit">{{ saving ? '保存中…' : '保存草稿' }}</button><button class="secondary" :disabled="reindexing || currentRole === 'sales'" @click="reindex">{{ reindexing ? '索引中…' : '重建向量索引' }}</button><button class="secondary" :disabled="evaluating || currentRole === 'sales'" @click="runEvaluation">{{ evaluating ? '评测中…' : '运行 RAG 评测' }}</button><button v-if="editingId !== null" class="secondary" @click="resetForm">取消编辑</button></div>
      <div v-if="evaluation" class="evaluation"><strong>召回评测（Top {{ evaluation.k }}）</strong><span>关键词 Hit@K：{{ (evaluation.summary.keyword.hit_at_k * 100).toFixed(0) }}%</span><span>向量 Hit@K：{{ (evaluation.summary.vector.hit_at_k * 100).toFixed(0) }}%</span></div>
    </section>
    <p v-if="loading">加载中…</p>
    <p v-else-if="!documents.length" class="empty">暂无知识文档。</p>
    <section v-else class="document-list">
      <article v-for="document in documents" :key="document.id" class="document-card">
        <div class="document-head"><div><h2>{{ document.title }}</h2><p>{{ document.slug }} · {{ document.category }} · v{{ document.version }} · {{ document.chunks.length }} 个分片</p><p class="index-meta">向量索引：{{ indexStatusLabel(document.vector_index_status) }} · 尝试 {{ document.vector_index_attempts }} 次</p></div><span class="status" :data-status="document.status">{{ document.status }}</span></div>
        <p class="preview">{{ document.chunks[0]?.content || '暂无正文' }}</p>
        <div class="actions"><button class="secondary" :disabled="currentRole === 'sales'" @click="edit(document)">编辑</button><button :disabled="currentRole === 'sales'" @click="transition(document, action(document).status)">{{ action(document).label }}</button></div>
      </article>
    </section>
  </div>
</template>

<style scoped>
.admin-page { display: grid; gap: 20px; }.page-header { display: flex; justify-content: space-between; gap: 16px; }.page-header h1 { margin: 0; }.eyebrow { margin: 0 0 6px; color: #0f766e; font-size: 12px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }.page-header p:last-child, .empty { color: #64748b; }.role-badge, .status { align-self: flex-start; padding: 6px 10px; border-radius: 999px; color: #1d4ed8; background: #dbeafe; font-size: 12px; }.status[data-status="published"] { color: #166534; background: #dcfce7; }.status[data-status="disabled"] { color: #64748b; background: #e2e8f0; }.panel, .document-card { padding: 20px; border: 1px solid #dbe5f3; border-radius: 16px; background: white; box-shadow: 0 8px 22px rgb(30 64 175 / 5%); }.panel h2 { margin-top: 0; }.form-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }label { display: grid; gap: 6px; color: #475569; font-size: 13px; }.wide { grid-column: 1 / -1; }input, textarea { box-sizing: border-box; width: 100%; padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; font: inherit; }textarea { resize: vertical; }.actions { display: flex; gap: 8px; margin-top: 14px; }button { padding: 9px 14px; border: 0; border-radius: 8px; color: white; background: #2563eb; cursor: pointer; }button:disabled { cursor: not-allowed; opacity: .5; }.secondary { color: #1e40af; background: #eff6ff; }.document-list { display: grid; gap: 14px; }.document-head { display: flex; justify-content: space-between; gap: 12px; }.document-head h2 { margin: 0; font-size: 18px; }.document-head p, .preview { color: #64748b; }.preview { white-space: pre-wrap; line-height: 1.6; }.error { color: #b91c1c; }
 .notice { color: #166534; }.index-meta { color: #475569 !important; font-size: 12px; }
.evaluation { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 14px; padding: 12px; border-radius: 10px; color: #334155; background: #f8fafc; font-size: 13px; }
@media (max-width: 700px) { .form-grid { grid-template-columns: 1fr; }.wide { grid-column: auto; }.page-header { flex-direction: column; } }
</style>
