export interface Organization {
  id: number
  parent_id: number | null
  name: string
  type: string
  path: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface OrganizationCreate {
  name: string
  type: string
  parent_id?: number | null
}
