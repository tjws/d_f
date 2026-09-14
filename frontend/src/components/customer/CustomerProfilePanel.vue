<script setup lang="ts">
import { ref, watch } from 'vue'
import type {
  CustomerProfile,
  CustomerProfileUpdate,
} from '../../types/customerProfile'

const props = defineProps<{
  profile: CustomerProfile | null
  error?: string
}>()

const emit = defineEmits<{
  generate: []
  edit: [profileId: number, payload: CustomerProfileUpdate]
  confirm: [profileId: number]
  reject: [profileId: number]
}>()

const dimensionsText = ref('{}')
const editError = ref('')

watch(
  () => props.profile,
  (profile) => {
    dimensionsText.value = profile
      ? JSON.stringify(profile.dimensions, null, 2)
      : '{}'
    editError.value = ''
  },
  { immediate: true },
)

function saveEdit(): void {
  try {
    const dimensions = JSON.parse(dimensionsText.value)
    if (!dimensions || typeof dimensions !== 'object' || Array.isArray(dimensions)) {
      throw new Error('画像内容必须是 JSON 对象')
    }
    editError.value = ''
    emit('edit', props.profile!.id, { dimensions })
  } catch (error) {
    editError.value = error instanceof Error ? error.message : 'JSON 格式错误'
  }
}
</script>

<template>
  <section class="panel">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">AI Profile</p>
        <h2>客户画像</h2>
      </div>
      <button type="button" @click="emit('generate')">
        生成草稿
      </button>
    </div>

    <p v-if="props.error" class="error">{{ props.error }}</p>
    <p v-if="!props.profile" class="muted">
      暂无画像。点击“生成草稿”开始。
    </p>

    <template v-else>
      <div class="status-row">
        <span>版本 {{ props.profile.version }}</span>
        <strong>{{ props.profile.status }}</strong>
      </div>

      <textarea v-model="dimensionsText" rows="9" />

      <p v-if="editError" class="error">{{ editError }}</p>

      <div class="actions">
        <button type="button" @click="saveEdit">保存编辑</button>
        <button
          type="button"
          class="success"
          :disabled="props.profile.status !== 'draft'"
          @click="emit('confirm', props.profile.id)"
        >
          人工确认
        </button>
        <button
          type="button"
          class="danger"
          :disabled="props.profile.status !== 'draft'"
          @click="emit('reject', props.profile.id)"
        >
          拒绝
        </button>
      </div>

      <details>
        <summary>查看证据</summary>
        <pre>{{ JSON.stringify(props.profile.evidence, null, 2) }}</pre>
      </details>
    </template>
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
.status-row,
.actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.eyebrow {
  margin: 0 0 6px;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

h2 {
  margin: 0 0 16px;
}

textarea {
  box-sizing: border-box;
  width: 100%;
  margin: 16px 0 8px;
  padding: 10px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-family: monospace;
}

button {
  padding: 8px 12px;
  border: 0;
  border-radius: 8px;
  color: white;
  background: #2563eb;
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.success {
  background: #16a34a;
}

.danger {
  background: #dc2626;
}

.muted,
.status-row {
  color: #64748b;
}

.error {
  color: #dc2626;
}

details {
  margin-top: 16px;
}

pre {
  max-height: 180px;
  overflow: auto;
  padding: 12px;
  border-radius: 8px;
  background: #f8fafc;
  font-size: 12px;
  white-space: pre-wrap;
}
</style>
