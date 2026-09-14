<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuth } from '../composables/useAuth'

const router = useRouter()
const route = useRoute()
const { signIn } = useAuth()

const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMessage = ref('')

async function submit(): Promise<void> {
  if (!username.value.trim() || !password.value) {
    errorMessage.value = '请输入用户名和密码'
    return
  }

  loading.value = true
  errorMessage.value = ''

  try {
    await signIn(username.value.trim(), password.value)
    const redirect = typeof route.query.redirect === 'string'
      ? route.query.redirect
      : '/customers'
    await router.replace(redirect)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <form class="login-card" @submit.prevent="submit">
      <p class="eyebrow">K12 Sales Assistant</p>
      <h1>登录系统</h1>
      <p class="description">登录后才能访问客户工作台和管理后台。</p>

      <label>
        用户名
        <input v-model="username" type="text" autocomplete="username" />
      </label>

      <label>
        密码
        <input v-model="password" type="password" autocomplete="current-password" />
      </label>

      <p v-if="errorMessage" class="error">{{ errorMessage }}</p>

      <button type="submit" :disabled="loading">
        {{ loading ? '登录中...' : '登录' }}
      </button>
    </form>
  </main>
</template>

<style scoped>
.login-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 24px;
  background: #eff6ff;
}

.login-card {
  box-sizing: border-box;
  width: min(100%, 420px);
  padding: 32px;
  border-radius: 20px;
  background: white;
  box-shadow: 0 18px 50px rgb(15 23 42 / 12%);
}

.eyebrow {
  margin: 0 0 8px;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

h1 {
  margin: 0;
}

.description {
  color: #64748b;
}

label {
  display: block;
  margin-top: 18px;
  color: #334155;
  font-weight: 600;
}

input {
  box-sizing: border-box;
  width: 100%;
  margin-top: 6px;
  padding: 11px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font: inherit;
}

button {
  width: 100%;
  margin-top: 22px;
  padding: 11px;
  border: 0;
  border-radius: 8px;
  color: white;
  background: #2563eb;
  cursor: pointer;
  font: inherit;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.error {
  color: #dc2626;
}
</style>
