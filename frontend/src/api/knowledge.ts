import { apiRequest } from './http'

export interface KnowledgeHit {
  document_id: string
  chunk_id?: number | null
  title: string
  snippet: string
  score: number
}

export type KnowledgeRetrievalMode = 'keyword' | 'vector' | 'mixed'

export interface KnowledgeSearchResponse {
  query: string
  matched: boolean
  retrieval_mode: KnowledgeRetrievalMode
  threshold: number
  fallback_message: string | null
  items: KnowledgeHit[]
}

export type KnowledgeStatus = 'draft' | 'published' | 'disabled'
export type KnowledgeIndexStatus = 'pending' | 'indexing' | 'ready' | 'failed' | 'disabled'

export interface KnowledgeChunk {
  id: number
  chunk_index: number
  content: string
}

export interface KnowledgeDocument {
  id: number
  slug: string
  title: string
  category: string
  source: string
  version: number
  status: KnowledgeStatus
  created_by: number | null
  published_by: number | null
  published_at: string | null
  created_at: string
  updated_at: string
  vector_index_status: KnowledgeIndexStatus
  vector_index_error: string | null
  vector_index_attempts: number
  vector_indexed_at: string | null
  vector_content_hash: string | null
  vector_embedding_model: string | null
  chunks: KnowledgeChunk[]
}

export interface KnowledgeDocumentCreate {
  slug: string
  title: string
  category: string
  source?: string
  content: string
}

export interface KnowledgeDocumentUpdate {
  title?: string
  category?: string
  content?: string
  status?: KnowledgeStatus
}

export interface KnowledgeEvaluationSummary {
  hit_at_k: number
  mean_reciprocal_rank: number
}

export interface KnowledgeEvaluationResult {
  k: number
  case_count: number
  summary: { keyword: KnowledgeEvaluationSummary; vector: KnowledgeEvaluationSummary }
  cases: Record<string, Array<{ query: string; hit: boolean; rank: number | null; matched_document_id: string | null }>>
}

export type RAGEvaluationCaseStatus = 'open' | 'reviewed' | 'ignored'

export interface RAGEvaluationCase {
  id: number
  interaction_id: number | null
  customer_id: number | null
  run_id: number | null
  actor_user_id: number | null
  source_type: string
  source_id: string
  query_excerpt: string | null
  retrieval_mode: string | null
  fallback: boolean
  expected_document_ids: string[] | null
  retrieved_document_ids: string[] | null
  status: RAGEvaluationCaseStatus
  review_note: string | null
  reviewed_by: number | null
  reviewed_at: string | null
  created_at: string
  updated_at: string
}

export interface RAGEvaluationReport {
  generated_at: string
  fixed_evaluation: KnowledgeEvaluationResult
  queue: { total: number; open: number; reviewed: number; ignored: number; fallback: number }
  cases: RAGEvaluationCase[]
}

export function listKnowledgeDocuments(): Promise<KnowledgeDocument[]> {
  return apiRequest<KnowledgeDocument[]>('/knowledge/admin')
}

export function createKnowledgeDocument(payload: KnowledgeDocumentCreate): Promise<KnowledgeDocument> {
  return apiRequest<KnowledgeDocument>('/knowledge/admin', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateKnowledgeDocument(documentId: number, payload: KnowledgeDocumentUpdate): Promise<KnowledgeDocument> {
  return apiRequest<KnowledgeDocument>(`/knowledge/admin/${documentId}`, { method: 'PATCH', body: JSON.stringify(payload) })
}

export function reindexKnowledgeVectors(): Promise<{ indexed: number; provider: string }> {
  return apiRequest('/knowledge/admin/reindex', { method: 'POST' })
}

export function evaluateKnowledge(limit = 3): Promise<KnowledgeEvaluationResult> {
  return apiRequest(`/knowledge/admin/evaluation?limit=${limit}`)
}

export function listRAGEvaluationCases(status?: RAGEvaluationCaseStatus): Promise<RAGEvaluationCase[]> {
  const params = new URLSearchParams({ limit: '100' })
  if (status) params.set('status', status)
  return apiRequest(`/knowledge/admin/evaluation-cases?${params.toString()}`)
}

export function getRAGEvaluationReport(limit = 3): Promise<RAGEvaluationReport> {
  return apiRequest(`/knowledge/admin/evaluation-report?limit=${limit}`)
}

export function reviewRAGEvaluationCase(
  caseId: number,
  payload: { status: RAGEvaluationCaseStatus; expected_document_ids: string[]; review_note?: string },
): Promise<RAGEvaluationCase> {
  return apiRequest(`/knowledge/admin/evaluation-cases/${caseId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function searchKnowledge(query: string, limit = 5): Promise<KnowledgeSearchResponse> {
  const params = new URLSearchParams({ q: query, limit: String(limit) })
  return apiRequest(`/knowledge/search?${params.toString()}`)
}
