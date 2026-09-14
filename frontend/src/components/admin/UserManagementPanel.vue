<script setup lang="ts">
import type { AdminUser, UserRole } from '../../types/adminUser'
import type { Organization } from '../../types/organization'

defineProps<{
  users: AdminUser[]
  organizations: Organization[]
  error?: string
}>()

const emit = defineEmits<{
  roleChange: [userId: number, role: UserRole]
  organizationChange: [userId: number, organizationId: number | null]
}>()

const roles: UserRole[] = ['sales', 'manager', 'admin']

function readValue(event: Event): string {
  return (event.target as HTMLSelectElement).value
}

function changeRole(userId: number, event: Event): void {
  const value = readValue(event)
  if (value === 'sales' || value === 'manager' || value === 'admin') {
    emit('roleChange', userId, value)
  }
}

function changeOrganization(userId: number, event: Event): void {
  const value = readValue(event)
  emit('organizationChange', userId, value ? Number(value) : null)
}
</script>

<template>
  <section class="panel">
    <header class="panel-header">
      <div>
        <p class="eyebrow">Users</p>
        <h2>用户管理</h2>
      </div>
      <span>{{ users.length }} users</span>
    </header>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="users.length === 0" class="muted">暂无用户或无权访问。</p>

    <div v-else class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>用户</th>
            <th>角色</th>
            <th>组织</th>
            <th>状态</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td>
              <strong>{{ user.full_name || user.username }}</strong>
              <small>{{ user.username }}</small>
            </td>
            <td>
              <select :value="user.role" @change="changeRole(user.id, $event)">
                <option v-for="role in roles" :key="role" :value="role">
                  {{ role }}
                </option>
              </select>
            </td>
            <td>
              <select
                :value="user.organization_id ?? ''"
                @change="changeOrganization(user.id, $event)"
              >
                <option value="">未分配</option>
                <option
                  v-for="organization in organizations"
                  :key="organization.id"
                  :value="organization.id"
                >
                  {{ organization.name }}
                </option>
              </select>
            </td>
            <td>{{ user.is_active ? 'active' : 'inactive' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
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
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

h2 {
  margin: 0 0 18px;
}

.table-wrapper {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  padding: 12px;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
  white-space: nowrap;
}

td small {
  display: block;
  margin-top: 4px;
  color: #64748b;
}

select {
  padding: 7px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  background: white;
}

.muted {
  color: #64748b;
}

.error {
  color: #dc2626;
}
</style>
