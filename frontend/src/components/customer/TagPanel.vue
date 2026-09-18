<script setup lang="ts">
import type { CustomerTag } from '../../types/tag'
import AIEvidencePanel from '../ai/AIEvidencePanel.vue'

const props = defineProps<{
  tags: CustomerTag[]
  error?: string
}>()

const emit = defineEmits<{
  generate: []
  confirm: [customerTagId: number]
  reject: [customerTagId: number]
}>()

const tagStatusLabels: Record<string, string> = {
  suggested: '待确认',
  confirmed: '已确认',
  rejected: '已拒绝',
}
</script>

<template>
  <section class="panel">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">AI Tags</p>
        <h2>客户标签</h2>
      </div>
      <button type="button" @click="emit('generate')">
        生成标签建议
      </button>
    </div>

    <p v-if="props.error" class="error">{{ props.error }}</p>
    <p v-if="props.tags.length === 0" class="muted">
      暂无标签建议。
    </p>

    <ul v-else class="tag-list">
      <li v-for="item in props.tags" :key="item.id" class="tag-item">
        <div>
          <strong>{{ item.tag.name }}</strong>
          <span>{{ tagStatusLabels[item.status] ?? item.status }} · {{ item.source === 'ai' ? 'AI 建议' : item.source }}</span>
        </div>

        <div v-if="item.status === 'suggested'" class="actions">
          <button type="button" class="success" @click="emit('confirm', item.id)">
            确认
          </button>
          <button type="button" class="danger" @click="emit('reject', item.id)">
            拒绝
          </button>
        </div>

        <AIEvidencePanel :evidence="item.evidence" />
      </li>
    </ul>
  </section>
</template>

<style scoped>
.panel {
  padding: 22px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: white;
}

.panel-heading,
.tag-item,
.actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.eyebrow {
  margin: 0 0 6px;
  color: #0891b2;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

h2 {
  margin: 0 0 16px;
}

button {
  padding: 8px 12px;
  border: 0;
  border-radius: 8px;
  color: white;
  background: #0891b2;
  cursor: pointer;
}

.success {
  background: #16a34a;
}

.danger {
  background: #dc2626;
}

.tag-list {
  display: grid;
  gap: 10px;
  padding: 0;
  list-style: none;
}

.tag-item {
  display: block;
  padding: 12px;
  border-radius: 10px;
  background: #f0fdfa;
}

.tag-item > div:first-child {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.tag-item span {
  display: block;
  margin-top: 4px;
  color: #64748b;
  font-size: 13px;
}

.muted {
  color: #64748b;
}

.error {
  color: #dc2626;
}
</style>
