import { reactive, ref } from 'vue'
import {
  listAdminUsers,
  updateUserOrganization,
  updateUserRole,
} from '../api/adminUsers'
import {
  createOrganization,
  listOrganizations,
} from '../api/organizations'
import { listAuditLogs, type AuditLogQuery } from '../api/auditLogs'
import type { AdminUser, UserRole } from '../types/adminUser'
import type { Organization, OrganizationCreate } from '../types/organization'
import type { AuditLog } from '../types/auditLog'

export function useAdminConsole() {
  const users = ref<AdminUser[]>([])
  const organizations = ref<Organization[]>([])
  const auditLogs = ref<AuditLog[]>([])
  const auditTotal = ref(0)
  const auditPage = ref(1)
  const auditPageSize = ref(20)
  const loading = ref(false)
  const errors = reactive<Record<string, string>>({})

  function setError(key: string, error: unknown): void {
    errors[key] = error instanceof Error ? error.message : '请求失败'
  }

  function clearError(key: string): void {
    delete errors[key]
  }

  async function loadUsers(): Promise<void> {
    try {
      clearError('users')
      users.value = await listAdminUsers()
    } catch (error) {
      setError('users', error)
    }
  }

  async function loadOrganizations(): Promise<void> {
    try {
      clearError('organizations')
      organizations.value = await listOrganizations()
    } catch (error) {
      setError('organizations', error)
    }
  }

  async function loadAuditLogs(params: AuditLogQuery = {}): Promise<void> {
    try {
      clearError('auditLogs')
      const response = await listAuditLogs({
        page: params.page ?? auditPage.value,
        page_size: params.page_size ?? auditPageSize.value,
        ...params,
      })
      auditLogs.value = response.items
      auditTotal.value = response.total
      auditPage.value = response.page
      auditPageSize.value = response.page_size
    } catch (error) {
      setError('auditLogs', error)
    }
  }

  async function loadAdminData(): Promise<void> {
    loading.value = true
    await Promise.allSettled([
      loadUsers(),
      loadOrganizations(),
      loadAuditLogs({ page: 1 }),
    ])
    loading.value = false
  }

  async function changeRole(userId: number, role: UserRole): Promise<void> {
    await updateUserRole(userId, role)
    await Promise.all([loadUsers(), loadAuditLogs({ page: 1 })])
  }

  async function assignOrganization(
    userId: number,
    organizationId: number | null,
  ): Promise<void> {
    await updateUserOrganization(userId, organizationId)
    await Promise.all([loadUsers(), loadAuditLogs({ page: 1 })])
  }

  async function addOrganization(payload: OrganizationCreate): Promise<void> {
    await createOrganization(payload)
    await Promise.all([loadOrganizations(), loadAuditLogs({ page: 1 })])
  }

  return {
    users,
    organizations,
    auditLogs,
    auditTotal,
    auditPage,
    auditPageSize,
    loading,
    errors,
    loadUsers,
    loadOrganizations,
    loadAuditLogs,
    loadAdminData,
    changeRole,
    assignOrganization,
    addOrganization,
  }
}
