import { API_BASE_URL } from './http'

export type ExportDataset = 'customers' | 'chat_messages' | 'audit_logs' | 'ai_feedback'
export type ExportFormat = 'csv' | 'json'

export interface DataRetentionPolicy {
  automatic_deletion_enabled: boolean
  default_export_redacted: boolean
  requires_admin: boolean
  review_before_delete: boolean
  datasets: string[]
  note: string
  retention_days: Record<string, number>
}

export interface RetentionDatasetPolicy {
  dataset: string
  retention_days: number
  automatic_deletion_allowed: boolean
  note: string
}

export interface DetailedRetentionPolicy {
  automatic_deletion_enabled: boolean
  configured_at: string
  datasets: RetentionDatasetPolicy[]
  non_deletable_datasets: string[]
  note: string
}

export interface RetentionPreview {
  dataset: string
  before: string
  matching_rows: number
  oldest_created_at: string | null
  newest_created_at: string | null
  deletion_allowed: boolean
}

async function authorizedFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const accessToken = sessionStorage.getItem('access_token')
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      ...options.headers,
    },
  })
  if (!response.ok) {
    if (response.status === 401) {
      sessionStorage.removeItem('access_token')
      window.dispatchEvent(new Event('auth:unauthorized'))
    }
    throw new Error(`API request failed: ${response.status} ${await response.text()}`)
  }
  return response
}

export async function getDataRetentionPolicy(): Promise<DataRetentionPolicy> {
  const response = await authorizedFetch('/admin/data-export/policy')
  return response.json() as Promise<DataRetentionPolicy>
}

export async function getDetailedRetentionPolicy(): Promise<DetailedRetentionPolicy> {
  const response = await authorizedFetch('/admin/data-retention')
  return response.json() as Promise<DetailedRetentionPolicy>
}

export async function previewRetention(dataset: string): Promise<RetentionPreview> {
  const response = await authorizedFetch('/admin/data-retention/preview', { method: 'POST', body: JSON.stringify({ dataset }) })
  return response.json() as Promise<RetentionPreview>
}

export async function purgeRetention(dataset: string, confirm = false): Promise<{ deleted_rows: number; audit_log_id: number | null }> {
  const response = await authorizedFetch('/admin/data-retention/purge', { method: 'POST', body: JSON.stringify({ dataset, confirm }) })
  return response.json() as Promise<{ deleted_rows: number; audit_log_id: number | null }>
}

export async function downloadAdminDataExport(params: {
  dataset: ExportDataset
  format: ExportFormat
  start?: string
  end?: string
  limit?: number
}): Promise<{ blob: Blob; filename: string }> {
  const query = new URLSearchParams({ format: params.format, limit: String(params.limit ?? 1000) })
  if (params.start) query.set('start', `${params.start}T00:00:00Z`)
  if (params.end) query.set('end', `${params.end}T23:59:59Z`)
  const response = await authorizedFetch(`/admin/data-export/${params.dataset}?${query.toString()}`)
  const header = response.headers.get('Content-Disposition') || ''
  const filename = header.match(/filename="([^"]+)"/)?.[1] || `k12-${params.dataset}-export.${params.format}`
  return { blob: await response.blob(), filename }
}
