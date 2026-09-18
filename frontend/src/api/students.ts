import { apiRequest } from './http'
import type { Student, StudentCreate, StudentUpdate } from '../types/student'

export function listStudents(customerId: number, includeArchived = false): Promise<Student[]> {
  const suffix = includeArchived ? '?include_archived=true' : ''
  return apiRequest<Student[]>(`/customers/${customerId}/students${suffix}`)
}

export function createStudent(
  customerId: number,
  payload: StudentCreate,
): Promise<Student> {
  return apiRequest<Student>(`/customers/${customerId}/students`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateStudent(customerId: number, studentId: number, payload: StudentUpdate): Promise<Student> {
  return apiRequest<Student>(`/customers/${customerId}/students/${studentId}`, { method: 'PATCH', body: JSON.stringify(payload) })
}

export function archiveStudent(customerId: number, studentId: number): Promise<Student> {
  return apiRequest<Student>(`/customers/${customerId}/students/${studentId}/archive`, { method: 'POST' })
}

export function restoreStudent(customerId: number, studentId: number): Promise<Student> {
  return apiRequest<Student>(`/customers/${customerId}/students/${studentId}/restore`, { method: 'POST' })
}
