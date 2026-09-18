import { apiRequest } from './http'
import type { CourseOrder, CourseOrderCreate, CourseOrderUpdate } from '../types/courseOrder'

export function listCourseOrders(customerId: number): Promise<CourseOrder[]> {
  return apiRequest<CourseOrder[]>(`/customers/${customerId}/orders`)
}

export function createCourseOrder(customerId: number, payload: CourseOrderCreate): Promise<CourseOrder> {
  return apiRequest<CourseOrder>(`/customers/${customerId}/orders`, { method: 'POST', body: JSON.stringify(payload) })
}

export function updateCourseOrder(customerId: number, orderId: number, payload: CourseOrderUpdate): Promise<CourseOrder> {
  return apiRequest<CourseOrder>(`/customers/${customerId}/orders/${orderId}`, { method: 'PATCH', body: JSON.stringify(payload) })
}
