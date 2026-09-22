<script setup lang="ts">
import { computed, ref } from 'vue'
import { searchKnowledge, type KnowledgeHit } from '../../api/knowledge'
import type { ChatMessage } from '../../types/chatMessage'

const props = defineProps<{
  messages: ChatMessage[]
  generating?: boolean
}>()

const emit = defineEmits<{
  generate: []
}>()

const loading = ref(false)
const error = ref('')
const results = ref<KnowledgeHit[]>([])
const hasSearched = ref(false)
const selectedDocumentId = ref<string | null>(null)

const latestCustomerQuestion = computed(() => {
  const inbound = [...props.messages]
    .filter((message) => message.direction === 'inbound')
    .sort((left, right) => new Date(right.sent_at).getTime() - new Date(left.sent_at).getTime())[0]
  return inbound?.content_masked || inbound?.content || ''
})

async function findMaterials(): Promise<void> {
  if (!latestCustomerQuestion.value || loading.value) return
  loading.value = true
  error.value = ''
  hasSearched.value = true
  try {
    const response = await searchKnowledge(latestCustomerQuestion.value, 4)
    results.value = response.items
    selectedDocumentId.value = response.items[0]?.document_id ?? null
  } catch (reason) {
    results.value = []
    error.value = reason instanceof Error ? reason.message : '销售资料查询失败'
  } finally {
    loading.value = false
  }
}

function selected(item: KnowledgeHit): boolean {
  return selectedDocumentId.value === item.document_id
}
</script>

<template>
  <aside class="panel material-panel">
    <p class="eyebrow">Sales Materials</p>
    <h2>推荐销售资料</h2>
    <p v-if="!latestCustomerQuestion" class="muted">收到家长消息后，可在这里查找适用的试听、课程和跟进资料。</p>
    <template v-else>
      <div class="question-box"><span>家长当前问题</span><strong>{{ latestCustomerQuestion }}</strong></div>
      <button type="button" :disabled="loading" @click="findMaterials">{{ loading ? '正在查找…' : '查找适用资料' }}</button>
      <p v-if="error" class="error">{{ error }}</p>
      <p v-else-if="hasSearched && results.length === 0" class="muted">没有找到足够依据。建议人工核实后再回复。</p>
      <div v-for="item in results" :key="`${item.document_id}-${item.chunk_id ?? 'document'}`" class="material" :class="{ selected: selected(item) }" @click="selectedDocumentId = item.document_id">
        <strong>{{ item.title }}</strong>
        <span>适用于当前家长的咨询，可作为回复依据</span>
        <p>{{ item.snippet }}</p>
      </div>
      <div v-if="results.length" class="material-action">
        <p>生成回复时，系统会根据当前问题重新检索并参考匹配资料；发送前仍需人工确认。</p>
        <button type="button" :disabled="props.generating" @click="emit('generate')">用资料生成回复建议</button>
      </div>
    </template>
  </aside>
</template>

<style scoped>
.panel { padding: 20px; border: 1px solid #d9e5f5; border-radius: 16px; background: linear-gradient(160deg, #fff, #f8fbff); }.eyebrow { margin: 0 0 6px; color: #0f766e; font-size: 12px; font-weight: 800; letter-spacing: .11em; text-transform: uppercase; }h2 { margin: 0 0 14px; color: #17335b; font-size: 21px; }.question-box { display: grid; gap: 5px; margin-bottom: 12px; padding: 11px; border-radius: 10px; background: #eef6ff; }.question-box span, .material span, .muted { color: #64748b; font-size: 12px; }.question-box strong { color: #334155; line-height: 1.5; }.material { margin-top: 10px; padding: 12px; border: 1px solid #e2e8f0; border-radius: 10px; background: white; cursor: pointer; }.material.selected { border-color: #34d399; box-shadow: 0 0 0 2px rgb(52 211 153 / 15%); }.material strong, .material span { display: block; }.material span { margin-top: 4px; }.material p { margin: 8px 0 0; color: #475569; font-size: 13px; line-height: 1.6; }.material-action { margin-top: 14px; padding-top: 12px; border-top: 1px solid #dbe5f1; }.material-action p { color: #64748b; font-size: 12px; line-height: 1.5; }button { padding: 8px 12px; border: 0; border-radius: 8px; color: white; background: #0f766e; cursor: pointer; font-weight: 700; }button:disabled { opacity: .55; cursor: wait; }.error { color: #b91c1c; font-size: 13px; }
</style>
