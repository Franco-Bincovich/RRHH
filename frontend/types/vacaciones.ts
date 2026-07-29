export type EstadoVacacion = "planificada" | "tomada" | "cancelada"
export type TipoVacacion = "vacaciones" | "semana_free" | "dia_free" | "permiso_especial"

export interface SolicitudVacaciones {
  id: string
  empresa_id: string
  empresa_nombre: string | null
  empleado_id: string
  empleado_nombre: string | null
  area_id: string | null
  area_nombre: string | null
  fecha_desde: string  // ISO date "YYYY-MM-DD"
  fecha_hasta: string  // ISO date "YYYY-MM-DD"
  dias: number
  tipo: TipoVacacion
  comentario: string | null
  cancelada: boolean
  estado: EstadoVacacion  // derivado por el backend
  /** Año al que CORRESPONDE la licencia; puede diferir del año de fecha_desde. */
  periodo: number | null
  dias_liquidados: number
  created_at: string
}

export interface SolicitudVacacionesCreate {
  empleado_id: string
  fecha_desde: string
  fecha_hasta: string
  tipo?: TipoVacacion
  comentario?: string
  periodo?: number
  dias_liquidados?: number
}

export interface SolicitudVacacionesUpdate {
  comentario?: string
  tipo?: TipoVacacion
  periodo?: number
  dias_liquidados?: number
}

/**
 * Días de un período que NO se tomaron. Viven en otra tabla porque no tienen fechas
 * (nadie faltó ningún día) — el porqué está en backend/migrations/083.
 *
 * `dias_liquidados` es un entero y no un bool: admite liquidación parcial. La UI lo muestra
 * como un tilde (tildado → dias_liquidados = dias).
 */
export interface VacacionPendiente {
  id: string
  empresa_id: string
  empresa_nombre: string | null
  empleado_id: string
  empleado_nombre: string | null
  area_id: string | null
  area_nombre: string | null
  periodo: number
  dias: number
  dias_liquidados: number
  comentario: string | null
  created_at: string
}

export interface VacacionPendienteCreate {
  empleado_id: string
  periodo: number
  dias: number
  dias_liquidados?: number
  comentario?: string
}

export interface VacacionPendienteListResponse {
  items: VacacionPendiente[]
  total: number
}

export interface SolicitudVacacionesListResponse {
  items: SolicitudVacaciones[]
  total: number
}

export interface SaldoVacaciones {
  empleado_id: string
  asignados: number
  gozados: number
  pedidos: number
  disponibles: number
}
