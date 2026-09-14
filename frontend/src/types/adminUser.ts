export type UserRole = 'sales' | 'manager' | 'admin'

export interface AdminUser {
  id: number
  username: string
  full_name: string | null
  role: UserRole
  organization_id: number | null
  is_active: boolean
  created_at: string
}
