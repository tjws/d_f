<script setup lang="ts">
import type { AIModelMeta } from '../../types/ai'

const props = defineProps<{
  meta: AIModelMeta
}>()

const evidenceLevelLabels: Record<string, string> = {
  normal: '一般',
  sufficient: '较充分',
}

function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN')
}
</script>

<template>
  <div class="model-meta">
    <span>模型：{{ props.meta.model_name }} · {{ props.meta.model_version }}</span>
    <span>生成于：{{ formatDate(props.meta.created_at) }}</span>
    <span v-if="props.meta.evidence_level">
      证据等级：{{ evidenceLevelLabels[props.meta.evidence_level] ?? props.meta.evidence_level }}
    </span>
    <span class="human-boundary">AI 草稿，必须人工确认</span>
  </div>
</template>

<style scoped>
.model-meta { display: flex; flex-wrap: wrap; gap: 6px 12px; margin: 14px 0; color: #64748b; font-size: 12px; }
.human-boundary { color: #b45309; font-weight: 700; }
</style>
