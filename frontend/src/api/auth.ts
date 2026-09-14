import { API_BASE_URL } from './http'
import type { TokenResponse } from '../types/auth'

export async function login(
  username: string,
  password: string,
): Promise<TokenResponse> {
  const body = new URLSearchParams({ username, password })
  const response = await fetch(`${API_BASE_URL}/auth/token`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body,
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(`登录失败：${response.status} ${detail}`)
  }

  return response.json() as Promise<TokenResponse>
}
