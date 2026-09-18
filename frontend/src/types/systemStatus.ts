export type DependencyState = 'ok' | 'error' | 'disabled'

export interface SystemStatus {
  checked_at: string
  ready: boolean
  dependencies: Record<string, { status: DependencyState }>
  ai: {
    default_provider: string
    workflow_providers: Record<string, string>
    embedding_provider: string
    embedding_model: string
    bailian_api_key_configured: boolean
  }
  worker: {
    required: boolean
    status: 'online' | 'offline' | 'error' | 'disabled'
    worker_id: string | null
    last_seen_at: string | null
    queue_depths: Record<string, number>
  }
  backup: {
    configured: boolean
    directory: string
    latest_backup_at: string | null
    latest_backup_name: string | null
    latest_size_bytes: number | null
    age_seconds: number | null
    status: 'ok' | 'missing' | 'stale' | 'disabled'
    max_age_hours: number
    automatic_prune_enabled: boolean
  }
}
