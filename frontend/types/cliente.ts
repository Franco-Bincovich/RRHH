/**
 * Espejo de backend/schemas/cliente.py.
 *
 * 🔴 SIN `empresa_id` (migración 108): un cliente no pertenece a ninguna empresa. El catálogo es
 * global — se ve, se crea y se da de baja con el selector del sidebar en cualquier modo, y
 * cualquier empleado imputa horas contra cualquier cliente. Revierte la decisión de la 102.
 */
export interface Cliente {
  id: string
  nombre: string
  activo: boolean
  created_at: string
  updated_at: string | null
}

export interface ClienteCreate {
  nombre: string
}

export interface ClienteUpdate {
  nombre?: string
  activo?: boolean
}

export interface ClienteListResponse {
  items: Cliente[]
  total: number
}
