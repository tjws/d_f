<script setup lang="ts">
import { RouterView, useRouter } from 'vue-router'
import { useAuth } from './composables/useAuth'

const router = useRouter()
const { isAuthenticated, signOut } = useAuth()

function logout(): void {
  signOut()
  void router.replace({ name: 'login' })
}
</script>

<template>
  <header v-if="isAuthenticated" class="session-bar">
    <span>已登录</span>
    <button type="button" @click="logout">退出登录</button>
  </header>
  <RouterView />
</template>

<style scoped>
.session-bar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding: 8px 6vw;
  color: #475569;
  background: #e0e7ff;
  font-size: 13px;
}

button {
  padding: 5px 10px;
  border: 0;
  border-radius: 6px;
  color: white;
  background: #4338ca;
  cursor: pointer;
}
</style>
