import { computed, ref } from 'vue'
import { login } from '../api/auth'

const token = ref<string | null>(sessionStorage.getItem('access_token'))

if (typeof window !== 'undefined') {
  window.addEventListener('auth:unauthorized', () => {
    token.value = null
  })
}

export function hasAccessToken(): boolean {
  return Boolean(sessionStorage.getItem('access_token'))
}

export function useAuth() {
  const isAuthenticated = computed(() => Boolean(token.value))

  async function signIn(username: string, password: string): Promise<void> {
    const response = await login(username, password)
    sessionStorage.setItem('access_token', response.access_token)
    token.value = response.access_token
  }

  function signOut(): void {
    sessionStorage.removeItem('access_token')
    token.value = null
  }

  return {
    isAuthenticated,
    signIn,
    signOut,
  }
}
