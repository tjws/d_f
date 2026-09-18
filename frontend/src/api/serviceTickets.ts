import { apiRequest } from './http'
import type { ServiceTicket, ServiceTicketCreate, ServiceTicketUpdate } from '../types/serviceTicket'

export function listServiceTickets(customerId: number): Promise<ServiceTicket[]> {
  return apiRequest<ServiceTicket[]>(`/customers/${customerId}/service-tickets`)
}

export function createServiceTicket(customerId: number, payload: ServiceTicketCreate): Promise<ServiceTicket> {
  return apiRequest<ServiceTicket>(`/customers/${customerId}/service-tickets`, { method: 'POST', body: JSON.stringify(payload) })
}

export function updateServiceTicket(customerId: number, ticketId: number, payload: ServiceTicketUpdate): Promise<ServiceTicket> {
  return apiRequest<ServiceTicket>(`/customers/${customerId}/service-tickets/${ticketId}`, { method: 'PATCH', body: JSON.stringify(payload) })
}
