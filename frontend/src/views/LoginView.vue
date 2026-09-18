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
      <div class="brand-mark">◆</div>
      <p class="eyebrow">K12 Sales Assistant</p>
      <h1>销售辅助系统</h1>
      <p class="description">登录后访问客户工作台与管理后台</p>

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
  padding: 32px 20px;
  background: radial-gradient(circle at 15% 10%, #dbeafe 0, transparent 38%), linear-gradient(135deg, #eef5ff, #e8eef8);
}

.login-card {
  box-sizing: border-box;
  width: min(100%, 460px);
  padding: 42px 44px 38px;
  border: 1px solid rgb(255 255 255 / 80%);
  border-radius: 24px;
  background: rgb(255 255 255 / 94%);
  box-shadow: 0 24px 70px rgb(30 64 175 / 15%);
  text-align: center;
}

.brand-mark { display: grid; width: 42px; height: 42px; margin: 0 auto 18px; place-items: center; border-radius: 14px; color: white; background: linear-gradient(135deg, #2563eb, #4f46e5); box-shadow: 0 8px 20px rgb(37 99 235 / 24%); }

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
  font-size: clamp(30px, 7vw, 40px);
  line-height: 1.2;
}

.description {
  margin: 10px 0 26px;
  color: #64748b;
}

label {
  display: block;
  margin-top: 16px;
  color: #334155;
  text-align: left;
  font-weight: 600;
}

input {
  box-sizing: border-box;
  width: 100%;
  margin-top: 6px;
  padding: 13px 14px;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  background: #f8fbff;
  font: inherit;
}

button {
  width: 100%;
  margin-top: 26px;
  padding: 13px;
  border: 0;
  border-radius: 10px;
  color: white;
  background: linear-gradient(135deg, #2563eb, #4338ca);
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
