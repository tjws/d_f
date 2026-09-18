<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  getAdminPermissions,
  updateAdminPermission,
  type AdminPermission,
  type PermissionRole,
  type PermissionScope,
} from '../../api/adminPermissions'

const permissions = ref<AdminPermission[]>([])
const loading = ref(true)
const savingId = ref<number | null>(null)
const error = ref('')
const role = ref<PermissionRole | ''>('')
const moduleName = ref('')

const roleLabels: Record<PermissionRole, string> = { admin: '管理员', manager: '经理', sales: '销售' }
const scopeLabels: Record<PermissionScope, string> = { own: '本人客户', team: '团队', organization: '组织', all: '全部' }
const scopeOptions: PermissionScope[] = ['own', 'team', 'organization', 'all']
const moduleOptions = computed(() => [...new Set(permissions.value.map((item) => item.module))])

async function load(): Promise<void> {
  loading.value = true
  error.value = ''
  try {
    permissions.value = await getAdminPermissions({ role: role.value || undefined, module: moduleName.value || undefined })
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '权限矩阵加载失败'
  } finally {
    loading.value = false
  }
}

async function save(permission: AdminPermission, nextScope: PermissionScope): Promise<void> {
  if (permission.data_scope === nextScope) return
  savingId.value = permission.id
  error.value = ''
  try {
    const updated = await updateAdminPermission(permission.id, nextScope)
    const index = permissions.value.findIndex((item) => item.id === updated.id)
    if (index >= 0) permissions.value[index] = updated
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '权限更新失败'
  } finally {
    savingId.value = null
  }
}

function clearFilters(): void {
  role.value = ''
  moduleName.value = ''
  void load()
}

onMounted(load)
</script>

<template>
  <div class="admin-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">Permission Matrix</p>
        <h1>权限矩阵</h1>
        <p>查看角色、模块、动作和数据范围；只有管理员可以修改，修改会写入审计日志。</p>
      </div>
      <button type="button" :disabled="loading" @click="load">{{ loading ? '加载中…' : '刷新' }}</button>
    </header>

    <section class="filters panel">
      <label>角色<select v-model="role"><option value="">全部角色</option><option value="admin">管理员</option><option value="manager">经理</option><option value="sales">销售</option></select></label>
      <label>模块<select v-model="moduleName"><option value="">全部模块</option><option v-for="item in moduleOptions" :key="item" :value="item">{{ item }}</option></select></label>
      <button type="button" @click="load">应用筛选</button>
      <button type="button" class="secondary" @click="clearFilters">清除</button>
    </section>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-else-if="loading" class="muted">正在读取权限配置…</p>
    <section v-else class="panel table-wrap">
      <table>
        <thead><tr><th>角色</th><th>模块</th><th>动作</th><th>数据范围</th><th>更新时间</th></tr></thead>
        <tbody>
          <tr v-for="permission in permissions" :key="permission.id">
            <td><span class="role">{{ roleLabels[permission.role] }}</span></td>
            <td>{{ permission.module }}</td>
            <td><code>{{ permission.action }}</code></td>
            <td>
              <select :value="permission.data_scope" :disabled="permission.role === 'admin' || savingId === permission.id" @change="save(permission, ($event.target as HTMLSelectElement).value as PermissionScope)">
                <option v-for="scope in scopeOptions" :key="scope" :value="scope">{{ scopeLabels[scope] }}</option>
              </select>
              <small v-if="permission.role === 'admin'">管理员固定为全部范围</small>
            </td>
            <td>{{ new Date(permission.updated_at).toLocaleString('zh-CN') }}</td>
          </tr>
        </tbody>
      </table>
      <p v-if="!permissions.length" class="muted">没有符合条件的权限配置。</p>
    </section>
  </div>
</template>

<style scoped>
.admin-page { display: grid; gap: 18px; }
.page-header { display: flex; align-items: end; justify-content: space-between; gap: 20px; }
.page-header h1 { margin: 0; }
.page-header p:last-child, .muted { color: #64748b; }
.eyebrow { margin: 0 0 6px; color: #7c3aed; font-size: 12px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
button { padding: 9px 14px; border: 0; border-radius: 8px; color: white; background: #7c3aed; cursor: pointer; }
button:disabled { cursor: wait; opacity: .6; }
.panel { padding: 18px; border: 1px solid #dbe5ee; border-radius: 16px; background: white; box-shadow: 0 8px 22px rgb(124 58 237 / 5%); }
.filters { display: flex; align-items: end; flex-wrap: wrap; gap: 10px; }
.filters label { display: grid; gap: 4px; color: #475569; font-size: 13px; }
select { min-width: 140px; padding: 8px; border: 1px solid #cbd5e1; border-radius: 8px; background: white; }
.secondary { color: #475569; background: #e2e8f0; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 11px 8px; text-align: left; border-bottom: 1px solid #e2e8f0; white-space: nowrap; }
th { color: #475569; font-size: 12px; }
code { color: #475569; }
.role { padding: 4px 8px; border-radius: 999px; color: #5b21b6; background: #ede9fe; }
small { display: block; margin-top: 4px; color: #94a3b8; }
.error { color: #b91c1c; }
@media (max-width: 700px) { .page-header { align-items: flex-start; flex-direction: column; } .filters { align-items: stretch; flex-direction: column; } .filters label, .filters select { width: 100%; } }
</style>
