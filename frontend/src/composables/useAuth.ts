import { computed, ref } from 'vue'
import { login } from '../api/auth'

const token = ref<string | null>(sessionStorage.getItem('access_token'))

const savedRole = ref<string | null>(sessionStorage.getItem('user_role'))

if (typeof window !== 'undefined') {
  window.addEventListener('auth:unauthorized', () => {
    token.value = null
    savedRole.value = null
    sessionStorage.removeItem('user_role')
  })
}

export function hasAccessToken(): boolean {
  return Boolean(sessionStorage.getItem('access_token'))
}

export function useAuth() {
  const isAuthenticated = computed(() => Boolean(token.value))
  const currentRole = computed(() => savedRole.value)

  async function signIn(username: string, password: string): Promise<void> {
    const response = await login(username, password)
    sessionStorage.setItem('access_token', response.access_token)
    sessionStorage.setItem('user_role', response.role ?? '')
    token.value = response.access_token
    savedRole.value = response.role ?? null
  }

  function signOut(): void {
    sessionStorage.removeItem('access_token')
    sessionStorage.removeItem('user_role')
    token.value = null
    savedRole.value = null
  }

  return {
    isAuthenticated,
    currentRole,
    signIn,
    signOut,
  }
}
