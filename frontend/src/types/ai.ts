/** 后端返回的可追溯 AI 证据；事实内容已经在服务端完成脱敏。 */
export interface AIEvidence {
  source_type: string
  source_id: string
  fact: unknown
  title?: string
  chunk_id?: number | null
  snippet?: string
}

/** 画像和 AI 建议共同具备的模型元数据。 */
export interface AIModelMeta {
  model_name: string
  model_version: string
  created_at: string
  evidence_level?: string
}
