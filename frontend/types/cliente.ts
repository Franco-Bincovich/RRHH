/** Espejo de backend/schemas/cliente.py. */
export interface Cliente {
  id: string
  empresa_id: string
  nombre: string
  activo: boolean
  created_at: string
  updated_at: string | null
}

export interface ClienteCreate {
  empresa_id: string
  nombre: string
}

/** `empresa_id` NO es editable: mudar un cliente de empresa dejaría las horas ya cargadas
 *  imputadas a una sociedad que no es la que facturó. Espejo de ClienteUpdate del backend. */
export interface ClienteUpdate {
  nombre?: string
  activo?: boolean
}

export interface ClienteListResponse {
  items: Cliente[]
  total: number
}
