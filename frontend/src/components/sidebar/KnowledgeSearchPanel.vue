<script setup lang="ts">
import { ref } from 'vue'
import { searchKnowledge, type KnowledgeHit, type KnowledgeSearchResponse } from '../../api/knowledge'

const query = ref('')
const results = ref<KnowledgeHit[]>([])
const searchMeta = ref<KnowledgeSearchResponse | null>(null)
const loading = ref(false)
const error = ref('')

async function search(): Promise<void> {
  if (!query.value.trim() || loading.value) return
  loading.value = true
  error.value = ''
  try {
    searchMeta.value = await searchKnowledge(query.value.trim())
    results.value = searchMeta.value.items
  } catch (reason) {
    searchMeta.value = null
    results.value = []
    error.value = reason instanceof Error ? reason.message : '知识库查询失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <div class="heading"><div><p class="eyebrow">Local RAG</p><h2>销售资料</h2></div><small>Mock 检索</small></div>
    <form class="search" @submit.prevent="search"><input v-model="query" maxlength="200" placeholder="搜索试听、收费、跟进…" /><button type="submit" :disabled="loading || !query.trim()">{{ loading ? '检索中…' : '检索' }}</button></form>
    <p v-if="error" class="error">{{ error }}</p>
    <template v-else-if="searchMeta && !loading">
      <p v-if="searchMeta.matched" class="match-status">已找到达到证据阈值的资料（{{ searchMeta.retrieval_mode }}）</p>
      <p v-else class="fallback">{{ searchMeta.fallback_message || '没有找到足够依据，请人工核实后回复。' }}</p>
    </template>
    <p v-else-if="query && !loading && results.length === 0" class="muted">没有匹配资料。</p>
    <details v-for="item in results" :key="`${item.document_id}-${item.chunk_id ?? 'document'}`" open><summary>{{ item.title }} · 匹配 {{ item.score }}</summary><p>{{ item.snippet }}</p></details>
  </section>
</template>

<style scoped>
.panel { padding:16px; border:1px solid #dbe3f0; border-radius:14px; background:#fff; }.heading { display:flex; justify-content:space-between; }.eyebrow { margin:0 0 5px; color:#0f766e; font-size:11px; font-weight:800; letter-spacing:.1em; }.heading h2 { margin:0 0 12px; }.heading small,.muted { color:#64748b; }.search { display:flex; gap:6px; }.search input { min-width:0; flex:1; padding:8px; border:1px solid #cbd5e1; border-radius:8px; font:inherit; }.search button { padding:8px 10px; border:0; border-radius:8px; color:#fff; background:#0f766e; }.search button:disabled { opacity:.5; }.error { color:#b91c1c; }.match-status { color:#0f766e; font-size:13px; }.fallback { padding:10px; color:#92400e; background:#fffbeb; border-radius:8px; line-height:1.5; }details { margin-top:10px; color:#334155; font-size:13px; }details p { color:#64748b; line-height:1.5; }
</style>
