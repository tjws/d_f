<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { CustomerProfile, CustomerProfileUpdate } from '../../types/customerProfile'

const props = defineProps<{ profile: CustomerProfile | null; error?: string }>()
const emit = defineEmits<{ generate: []; edit: [profileId: number, payload: CustomerProfileUpdate]; confirm: [profileId: number]; reject: [profileId: number] }>()

const editing = ref(false)
const editableDimensions = ref<Record<string, string>>({})
const profileStatusLabels: Record<string, string> = { draft: '待人工确认', confirmed: '已确认', rejected: '已拒绝', archived: '已归档' }
const dimensionLabels: Record<string, string> = { summary: '整体情况', learning_needs: '学习情况', communication_preference: '沟通偏好', next_action: '下一步建议', risk_notes: '需要关注', risks: '需要关注', interests: '兴趣与关注点' }

function displayValue(value: unknown): string | null {
  if (typeof value === 'string' || typeof value === 'number') return String(value)
  if (Array.isArray(value)) return value.filter((item) => typeof item === 'string' || typeof item === 'number').join('、') || null
  return null
}

const profileItems = computed(() => Object.entries(props.profile?.dimensions ?? {})
  .map(([key, value]) => ({ key, label: dimensionLabels[key] ?? key.replaceAll('_', ' '), value: displayValue(value) }))
  .filter((item): item is { key: string; label: string; value: string } => item.value !== null))
const isDraft = computed(() => props.profile?.status === 'draft')

watch(() => props.profile, (profile) => {
  editableDimensions.value = Object.fromEntries(Object.entries(profile?.dimensions ?? {}).map(([key, value]) => [key, displayValue(value) ?? '']))
  editing.value = false
}, { immediate: true })

function saveEdit(): void {
  if (!props.profile) return
  emit('edit', props.profile.id, { dimensions: { ...props.profile.dimensions, ...editableDimensions.value } })
  editing.value = false
}
</script>

<template>
  <section class="panel">
    <div class="panel-heading"><div><p class="eyebrow">Customer Profile</p><h2>客户画像</h2></div><button type="button" @click="emit('generate')">生成草稿</button></div>
    <p v-if="props.error" class="error">{{ props.error }}</p>
    <p v-else-if="!props.profile" class="muted">暂无客户画像。生成草稿后，由你确认是否写入客户档案。</p>
    <template v-else>
      <div class="status-row"><span>版本 {{ props.profile.version }}</span><strong>{{ profileStatusLabels[props.profile.status] ?? props.profile.status }}</strong></div>
      <p class="human-note">这是 AI 整理的客户信息，请结合实际沟通判断；不会自动改变客户资料。</p>
      <p v-if="props.profile.status === 'confirmed'" class="confirmed-note">当前为已确认版本。如需调整，请生成一版新草稿后再审阅。</p>
      <dl v-if="!editing" class="profile-list"><template v-for="item in profileItems" :key="item.key"><dt>{{ item.label }}</dt><dd>{{ item.value }}</dd></template></dl>
      <p v-if="!editing && profileItems.length === 0" class="muted">当前画像没有可展示的文字内容，请重新生成或编辑。</p>
      <div v-if="isDraft" class="actions"><template v-if="editing"><button type="button" @click="saveEdit">保存编辑</button><button type="button" class="secondary" @click="editing = false">取消</button></template><template v-else><button type="button" class="secondary" @click="editing = true">编辑画像</button><button type="button" class="success" @click="emit('confirm', props.profile.id)">人工确认</button><button type="button" class="danger" @click="emit('reject', props.profile.id)">拒绝</button></template></div>
    </template>
  </section>
</template>

<style scoped>
.panel { padding: 22px; border: 1px solid #e2e8f0; border-radius: 16px; background: white; }.panel-heading, .status-row, .actions { display: flex; align-items: center; justify-content: space-between; gap: 10px; }.eyebrow { margin: 0 0 6px; color: #2563eb; font-size: 12px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; } h2 { margin: 0 0 16px; }.status-row { color: #64748b; }.status-row strong { color: #166534; }.human-note, .muted { color: #64748b; font-size: 13px; line-height: 1.6; }.confirmed-note { margin: 10px 0; padding: 9px 11px; border-radius: 8px; color: #166534; background: #ecfdf5; font-size: 13px; line-height: 1.55; }.profile-list { display: grid; grid-template-columns: 112px minmax(0, 1fr); gap: 12px 16px; margin: 18px 0; padding: 16px; border-radius: 12px; background: #f8fbff; }.profile-list dt { color: #64748b; font-size: 13px; }.profile-list dd { margin: 0; color: #1e293b; line-height: 1.65; }.edit-form { display: grid; gap: 10px; margin: 16px 0; }.edit-form label { display: grid; gap: 5px; color: #475569; font-size: 13px; font-weight: 700; } textarea { box-sizing: border-box; width: 100%; padding: 10px; border: 1px solid #cbd5e1; border-radius: 8px; font: inherit; }.actions { justify-content: flex-start; flex-wrap: wrap; } button { padding: 8px 12px; border: 0; border-radius: 8px; color: white; background: #2563eb; cursor: pointer; } button:disabled { cursor: not-allowed; opacity: .45; }.success { background: #16a34a; }.danger { background: #dc2626; }.secondary { color: #1e40af; background: #dbeafe; }.error { color: #dc2626; }
</style>
