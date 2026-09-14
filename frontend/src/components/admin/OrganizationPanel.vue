<script setup lang="ts">
import { reactive, ref } from 'vue'
import type {
  Organization,
  OrganizationCreate,
} from '../../types/organization'

const props = defineProps<{
  organizations: Organization[]
  error?: string
}>()

const emit = defineEmits<{
  create: [payload: OrganizationCreate]
}>()

const showForm = ref(false)
const form = reactive<OrganizationCreate>({
  name: '',
  type: 'team',
  parent_id: null,
})

function submit(): void {
  if (!form.name.trim() || !form.type.trim()) return
  emit('create', {
    name: form.name.trim(),
    type: form.type.trim(),
    parent_id: form.parent_id,
  })
  form.name = ''
  form.type = 'team'
  form.parent_id = null
  showForm.value = false
}
</script>

<template>
  <section class="panel">
    <header class="panel-header">
      <div>
        <p class="eyebrow">Organizations</p>
        <h2>组织管理</h2>
      </div>
      <button type="button" @click="showForm = !showForm">
        {{ showForm ? '取消' : '新建组织' }}
      </button>
    </header>

    <p v-if="props.error" class="error">{{ props.error }}</p>

    <form v-if="showForm" class="create-form" @submit.prevent="submit">
      <input v-model="form.name" placeholder="组织名称" />
      <input v-model="form.type" placeholder="组织类型，例如 team" />
      <select v-model="form.parent_id">
        <option :value="null">无父组织</option>
        <option
          v-for="organization in props.organizations"
          :key="organization.id"
          :value="organization.id"
        >
          {{ organization.name }}
        </option>
      </select>
      <button type="submit">保存</button>
    </form>

    <ul class="organization-list">
      <li v-for="organization in props.organizations" :key="organization.id">
        <strong>{{ organization.name }}</strong>
        <span>{{ organization.type }} · {{ organization.status }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.panel {
  padding: 24px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: white;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.eyebrow {
  margin: 0 0 6px;
  color: #16a34a;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

h2 {
  margin: 0 0 18px;
}

button {
  padding: 8px 12px;
  border: 0;
  border-radius: 8px;
  color: white;
  background: #16a34a;
  cursor: pointer;
}

.create-form {
  display: grid;
  gap: 8px;
  margin-bottom: 18px;
}

input,
select {
  padding: 9px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font: inherit;
}

.organization-list {
  display: grid;
  gap: 8px;
  padding: 0;
  list-style: none;
}

.organization-list li {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  background: #f0fdf4;
}

.organization-list span {
  color: #64748b;
  font-size: 13px;
}

.error {
  color: #dc2626;
}
</style>
