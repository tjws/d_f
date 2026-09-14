<script setup lang="ts">
import { onMounted, ref } from 'vue'
import UserManagementPanel from '../../components/admin/UserManagementPanel.vue'
import OrganizationPanel from '../../components/admin/OrganizationPanel.vue'
import { useAdminConsole } from '../../composables/useAdminConsole'
import type { UserRole } from '../../types/adminUser'
import type { OrganizationCreate } from '../../types/organization'

const {
  users,
  organizations,
  loading,
  errors,
  loadAdminData,
  changeRole,
  assignOrganization,
  addOrganization,
} = useAdminConsole()

const actionError = ref('')

async function handleRoleChange(userId: number, role: UserRole): Promise<void> {
  try {
    actionError.value = ''
    await changeRole(userId, role)
  } catch (error) {
    actionError.value = error instanceof Error ? error.message : '角色修改失败'
  }
}

async function handleOrganizationChange(
  userId: number,
  organizationId: number | null,
): Promise<void> {
  try {
    actionError.value = ''
    await assignOrganization(userId, organizationId)
  } catch (error) {
    actionError.value = error instanceof Error ? error.message : '组织分配失败'
  }
}

async function handleOrganizationCreate(
  payload: OrganizationCreate,
): Promise<void> {
  try {
    actionError.value = ''
    await addOrganization(payload)
  } catch (error) {
    actionError.value = error instanceof Error ? error.message : '组织创建失败'
  }
}

onMounted(loadAdminData)
</script>

<template>
  <div class="admin-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Administration</p>
        <h1>用户与组织</h1>
        <p>管理角色和组织归属，实际权限仍由后端校验。</p>
      </div>
      <span v-if="loading">加载中...</span>
    </header>

    <p v-if="actionError" class="error">{{ actionError }}</p>

    <div class="panel-grid">
      <UserManagementPanel
        :users="users"
        :organizations="organizations"
        :error="errors.users"
        @role-change="handleRoleChange"
        @organization-change="handleOrganizationChange"
      />

      <OrganizationPanel
        :organizations="organizations"
        :error="errors.organizations"
        @create="handleOrganizationCreate"
      />
    </div>
  </div>
</template>

<style scoped>
.admin-page {
  display: grid;
  gap: 20px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.eyebrow {
  margin: 0 0 6px;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

h1 {
  margin: 0;
}

.page-header p {
  color: #64748b;
}

.panel-grid {
  display: grid;
  gap: 20px;
}

.error {
  color: #dc2626;
}
</style>
