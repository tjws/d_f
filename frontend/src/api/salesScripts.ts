import { apiRequest } from './http'
import type { SalesScript, SalesScriptCreate, SalesScriptUpdate } from '../types/salesScript'

export function listSalesScripts(): Promise<SalesScript[]> {
  return apiRequest<SalesScript[]>('/admin/sales-scripts')
}

export function createSalesScript(payload: SalesScriptCreate): Promise<SalesScript> {
  return apiRequest<SalesScript>('/admin/sales-scripts', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateSalesScript(scriptId: number, payload: SalesScriptUpdate): Promise<SalesScript> {
  return apiRequest<SalesScript>(`/admin/sales-scripts/${scriptId}`, { method: 'PATCH', body: JSON.stringify(payload) })
}
