<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRouter } from 'vue-router'
import { useAuth } from './composables/useAuth'

const router = useRouter()
const { isAuthenticated, currentRole, signOut } = useAuth()
const canEnterAdmin = computed(() => currentRole.value === 'admin' || currentRole.value === 'manager')

function logout(): void {
  signOut()
  void router.replace({ name: 'login' })
}
</script>

<template>
  <header v-if="isAuthenticated" class="session-bar">
    <RouterLink to="/customers" class="brand"><span class="brand-mark">K</span><span>擎天学智<small>K12 SALES</small></span></RouterLink>
    <nav class="session-nav" aria-label="主要功能">
      <RouterLink to="/my-work">工作台</RouterLink>
      <RouterLink to="/customers">客户</RouterLink>
      <RouterLink to="/churn-risks">风险</RouterLink>
      <RouterLink v-if="canEnterAdmin" to="/admin">管理后台</RouterLink>
    </nav>
    <span class="session-status"><i /> 本地已登录</span>
    <button type="button" class="logout" @click="logout">退出</button>
  </header>
  <RouterView />
</template>

<style scoped>
.session-bar {
  position: sticky;
  z-index: 20;
  top: 0;
  display: flex;
  align-items: center;
  gap: 18px;
  min-height: 64px;
  padding: 10px clamp(18px, 5vw, 76px);
  color: #475569;
  background: rgb(255 255 255 / 88%);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid rgb(219 228 240 / 88%);
  box-shadow: 0 4px 18px rgb(15 23 42 / 4%);
  font-size: 13px;
}

.brand { display: inline-flex; align-items: center; gap: 10px; color: var(--ink); font-size: 15px; font-weight: 800; letter-spacing: -.02em; text-decoration: none; }.brand > span:last-child { display: grid; gap: 1px; }.brand small { color: #94a3b8; font-size: 8px; letter-spacing: .13em; }.brand-mark { display: grid; width: 32px; height: 32px; place-items: center; border-radius: 11px; color: white; background: linear-gradient(135deg, #1d4ed8, #4f46e5); box-shadow: 0 8px 17px rgb(37 99 235 / 24%); }
.session-status { display: inline-flex; align-items: center; gap: 7px; }
.session-status i { width: 7px; height: 7px; border-radius: 50%; background: #22c55e; box-shadow: 0 0 0 4px rgb(34 197 94 / 12%); }
.session-nav { display: flex; gap: 3px; margin-right: auto; }.session-nav a { padding: 8px 10px; border-radius: 9px; color: #64748b; text-decoration: none; white-space: nowrap; }.session-nav a:hover { color: #1d4ed8; background: #f1f5ff; }.session-nav a.router-link-active { color: #1d4ed8; background: #eaf1ff; font-weight: 800; }

button {
  padding: 7px 12px;
  border: 0;
  border-radius: 8px;
  color: white;
  background: #1e40af;
  cursor: pointer;
}
.logout { color: #475569; background: #eef2f7; }

@media (max-width: 720px) { .session-bar { gap: 8px; padding: 8px 14px; }.brand > span:last-child, .session-status { display: none; }.session-nav { overflow-x: auto; scrollbar-width: none; }.session-nav::-webkit-scrollbar { display: none; }.session-nav a { white-space: nowrap; } }
</style>
