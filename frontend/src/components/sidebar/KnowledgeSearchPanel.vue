<script setup lang="ts">
import { ref, watch } from 'vue'
import { searchKnowledge, type KnowledgeHit, type KnowledgeSearchResponse } from '../../api/knowledge'

const query = ref('')
const results = ref<KnowledgeHit[]>([])
const searchMeta = ref<KnowledgeSearchResponse | null>(null)
const hasSearched = ref(false)
const loading = ref(false)
const error = ref('')

async function search(): Promise<void> {
  if (!query.value.trim() || loading.value) return
  loading.value = true
  hasSearched.value = true
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

// 修改关键词后，旧结果不再代表当前问题；回到“待检索”状态，避免误导销售。
watch(query, () => {
  if (hasSearched.value) {
    hasSearched.value = false
    searchMeta.value = null
    results.value = []
  }
})

const props = defineProps<{ generating?: boolean; replyNotice?: string; replyError?: string }>()
const emit = defineEmits<{ generateReply: [] }>()
</script>

<template>
  <section class="panel">
    <div class="heading"><div><p class="eyebrow">Sales Knowledge</p><h2>销售资料</h2></div><small>按需检索</small></div>
    <form class="search" @submit.prevent="search"><input v-model="query" maxlength="200" placeholder="搜索试听、收费、跟进…" /><button type="submit" :disabled="loading || !query.trim()">{{ loading ? '检索中…' : '检索' }}</button></form>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-else-if="!hasSearched" class="guide">输入家长关心的问题后点击“检索”，查看可用于沟通的已审核资料。</p>
    <template v-else-if="searchMeta && !loading">
      <p v-if="searchMeta.matched" class="match-status">已找到可作为沟通依据的资料。确认内容后，可生成待审核的回复草稿。</p>
      <p v-else class="fallback">{{ searchMeta.fallback_message || '没有找到足够依据，请人工核实后回复。' }}</p>
    </template>
    <article v-for="item in results" :key="`${item.document_id}-${item.chunk_id ?? 'document'}`" class="material"><strong>{{ item.title }}</strong><span>可作为当前沟通的参考依据</span><p>{{ item.snippet }}</p></article>
    <div v-if="searchMeta?.matched && results.length" class="next-step">
      <p>生成回复时，系统会按客户最新一条消息重新检索资料并交给 AI；结果仍必须由你编辑、接受并确认发送。</p>
      <button type="button" class="generate" :disabled="props.generating" @click="emit('generateReply')">{{ props.generating ? '正在生成回复建议…' : '基于最新消息生成回复建议' }}</button>
      <p v-if="props.replyNotice" class="reply-notice">{{ props.replyNotice }}</p>
      <p v-if="props.replyError" class="error">{{ props.replyError }}</p>
    </div>
  </section>
</template>

<style scoped>
.panel { padding:16px; border:1px solid #dbe3f0; border-radius:14px; background:#fff; }.heading { display:flex; justify-content:space-between; }.eyebrow { margin:0 0 5px; color:#0f766e; font-size:11px; font-weight:800; letter-spacing:.1em; }.heading h2 { margin:0 0 12px; }.heading small,.guide { color:#64748b; }.search { display:flex; gap:6px; }.search input { min-width:0; flex:1; padding:8px; border:1px solid #cbd5e1; border-radius:8px; font:inherit; }.search button,.generate { padding:8px 10px; border:0; border-radius:8px; color:#fff; background:#0f766e; cursor:pointer; font:inherit; font-weight:700; }.search button:disabled,.generate:disabled { opacity:.5; cursor:wait; }.guide { margin:10px 0 0; font-size:12px; line-height:1.5; }.error { color:#b91c1c; }.match-status { color:#0f766e; font-size:13px; line-height:1.5; }.fallback { padding:10px; color:#92400e; background:#fffbeb; border-radius:8px; line-height:1.5; }.material { display:grid; gap:4px; margin-top:10px; padding:10px; border:1px solid #e2e8f0; border-radius:9px; background:#f8fafc; }.material strong { color:#1e3a5f; }.material span { color:#64748b; font-size:11px; }.material p { margin:0; color:#475569; font-size:12px; line-height:1.5; }.next-step { display:grid; gap:8px; margin-top:12px; padding-top:12px; border-top:1px solid #e2e8f0; }.next-step p { margin:0; color:#64748b; font-size:12px; line-height:1.5; }.generate { justify-self:start; background:#2563eb; }.reply-notice { margin:0; color:#166534 !important; font-weight:700; }
</style>
