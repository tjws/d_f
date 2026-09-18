import { apiRequest } from './http'
import type { MyWorkBucket, MyWorkResponse } from '../types/myWork'

export function getMyWork(bucket?: MyWorkBucket): Promise<MyWorkResponse> {
  return apiRequest<MyWorkResponse>(`/my-work${bucket ? `?bucket=${bucket}` : ''}`)
}
