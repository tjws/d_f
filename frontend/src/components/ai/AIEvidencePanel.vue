<script setup lang="ts">
import type { AIEvidence } from '../../types/ai'

const props = defineProps<{
  evidence: AIEvidence[]
}>()

const sourceLabels: Record<string, string> = {
  customer: '客户资料',
  customer_profile: '已确认客户画像',
  chat_message: '聊天记录',
  timeline_event: '客户时间线',
  schedule_completion: '人工回填跟进结果',
  student: '学生资料',
  knowledge: '知识库资料',
  sales_script: '审核销售话术',
}

function sourceLabel(sourceType: string): string {
  return sourceLabels[sourceType] ?? sourceType
}

function formatFact(value: unknown): string {
  if (typeof value === 'string') return value
  if (value === null || value === undefined) return '已关联系统记录'
  return JSON.stringify(value)
}
</script>

<template>
  <details class="evidence-panel">
    <summary>查看证据（{{ props.evidence.length }}）</summary>
    <p class="notice">证据来自系统已记录的脱敏资料，AI 结论仍需人工判断。</p>
    <p v-if="props.evidence.length === 0" class="muted">本次草稿没有可展示的证据。</p>
    <ul v-else>
      <li v-for="(item, index) in props.evidence" :key="`${item.source_type}-${item.source_id}-${index}`">
        <strong>{{ sourceLabel(item.source_type) }}</strong>
        <span>{{ formatFact(item.fact) }}</span>
        <small v-if="item.snippet">{{ item.snippet }}</small>
      </li>
    </ul>
  </details>
</template>

<style scoped>
.evidence-panel { margin-top: 16px; color: #475569; }
summary { cursor: pointer; color: #1d4ed8; font-size: 14px; font-weight: 700; }
.notice, .muted { margin: 10px 0; color: #64748b; font-size: 13px; }
ul { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; }
li { padding: 10px; border-radius: 8px; background: #f8fafc; font-size: 13px; }
strong, span { display: block; }
strong { margin-bottom: 3px; color: #334155; }
span { overflow-wrap: anywhere; }
small { display: block; margin-top: 6px; color: #64748b; line-height: 1.5; }
</style>
