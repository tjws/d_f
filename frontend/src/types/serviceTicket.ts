export type ServiceTicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed'

export interface ServiceTicket {
  id: number
  external_ticket_id: string
  customer_id: number
  type: string
  status: ServiceTicketStatus
  summary: string
  opened_at: string
  closed_at: string | null
  raw_snapshot: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface ServiceTicketCreate {
  external_ticket_id: string
  type: string
  summary: string
  status?: ServiceTicketStatus
}

export interface ServiceTicketUpdate {
  type?: string
  summary?: string
  status?: ServiceTicketStatus
}
