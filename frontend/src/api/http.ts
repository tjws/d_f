export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const accessToken = sessionStorage.getItem('access_token')
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...options.headers,
    },
  })

  if (!response.ok) {
    if (response.status === 401) {
      sessionStorage.removeItem('access_token')
      window.dispatchEvent(new Event('auth:unauthorized'))
    }
    const detail = await response.text()
    throw new Error(`API request failed: ${response.status} ${detail}`)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}
