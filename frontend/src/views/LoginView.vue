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
    <div class="login-layout">
      <section class="welcome-panel">
        <div class="brand-mark">K</div>
        <p class="eyebrow">K12 Sales Assistant</p>
        <h1>让每次家长沟通<br>都有据可循。</h1>
        <p>客户信息、跟进计划和 AI 建议会在同一工作台呈现；所有对外发送与业务决定，仍由你确认。</p>
        <div class="principles"><span>✓ 客户数据分权限访问</span><span>✓ AI 仅提供建议草稿</span><span>✓ 关键操作可追溯</span></div>
      </section>

      <form class="login-card" @submit.prevent="submit">
        <p class="eyebrow">欢迎回来</p>
        <h2>登录销售工作台</h2>
        <p class="description">输入账号后继续处理客户和待办。</p>

        <label>
          用户名
          <input v-model="username" type="text" autocomplete="username" placeholder="请输入用户名" />
        </label>

        <label>
          密码
          <input v-model="password" type="password" autocomplete="current-password" placeholder="请输入密码" />
        </label>

        <p v-if="errorMessage" class="error">{{ errorMessage }}</p>

        <button type="submit" :disabled="loading">
          {{ loading ? '正在验证…' : '登录并进入工作台' }}
        </button>
      </form>
    </div>
  </main>
</template>

<style scoped>
.login-page {
  display: grid;
  min-height: 100vh;
  place-items: center;
  padding: 32px 20px;
  background: radial-gradient(circle at 4% 2%, #dbeafe 0, transparent 34%), linear-gradient(135deg, #edf5ff, #f6f8fd);
}
.login-layout { display: grid; grid-template-columns: minmax(300px, 1fr) minmax(340px, 430px); gap: clamp(32px, 7vw, 112px); width: min(100%, 1100px); align-items: center; }
.welcome-panel { padding: 36px 18px; }.welcome-panel .brand-mark { display: grid; width: 48px; height: 48px; margin: 0 0 24px; place-items: center; border-radius: 15px; color: white; background: linear-gradient(135deg, #1d4ed8, #4f46e5); box-shadow: 0 11px 24px rgb(37 99 235 / 25%); font-size: 21px; font-weight: 900; }.eyebrow { margin: 0 0 9px; color: #2563eb; font-size: 12px; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; }.welcome-panel h1 { margin: 0; color: #172554; font-size: clamp(36px, 5vw, 58px); line-height: 1.13; }.welcome-panel > p:not(.eyebrow) { max-width: 540px; margin: 18px 0 0; color: #52647e; font-size: 16px; line-height: 1.8; }.principles { display: grid; gap: 9px; margin-top: 26px; color: #31527e; font-size: 14px; font-weight: 700; }.principles span { display: flex; align-items: center; gap: 8px; }.principles span::first-letter { color: #15803d; }
.login-card {
  box-sizing: border-box;
  width: min(100%, 460px);
  justify-self: end;
  padding: 38px 40px 36px;
  border: 1px solid rgb(255 255 255 / 84%);
  border-radius: 22px;
  background: rgb(255 255 255 / 92%);
  box-shadow: 0 24px 70px rgb(30 64 175 / 15%);
}
.login-card h2 {
  margin: 0;
  color: #172033;
  font-size: 28px;
  line-height: 1.2;
}
.description {
  margin: 10px 0 28px;
  color: #64748b;
  line-height: 1.6;
}
label {
  display: block;
  margin-top: 18px;
  color: #334155;
  text-align: left;
  font-weight: 600;
}

input {
  box-sizing: border-box;
  width: 100%;
  margin-top: 7px;
  padding: 13px 14px;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  background: #fbfdff;
  font: inherit;
}
input:focus { border-color: #2563eb; box-shadow: 0 0 0 4px rgb(37 99 235 / 10%); outline: 0; }
button {
  width: 100%;
  margin-top: 28px;
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
  margin: 16px 0 0;
  color: #dc2626;
}
@media (max-width: 760px) { .login-layout { grid-template-columns: 1fr; gap: 8px; max-width: 480px; }.welcome-panel { padding: 10px 6px 20px; }.welcome-panel h1 { font-size: 34px; }.welcome-panel > p:not(.eyebrow), .principles { display: none; }.login-card { width: 100%; justify-self: stretch; padding: 30px 26px; } }
</style>
