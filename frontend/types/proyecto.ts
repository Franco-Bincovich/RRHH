export type ProyectoEstado = "activo" | "pausado" | "cerrado" | "cancelado"

export interface CosteoResumen {
  costo_acumulado: number
  presupuesto_restante: number
  pct_consumido: number | null
}

export interface Proyecto {
  id: string
  empresa_id: string
  empresa_nombre: string | null
  nombre: string
  descripcion: string | null
  estado: ProyectoEstado
  fecha_inicio: string | null
  fecha_fin: string | null
  presupuesto: number
  costeo: CosteoResumen
  created_at: string
  updated_at: string | null
}

export interface ProyectoCreate {
  empresa_id: string
  nombre: string
  descripcion?: string
  estado?: ProyectoEstado
  fecha_inicio?: string
  fecha_fin?: string
  presupuesto?: number
}

export interface ProyectoUpdate {
  nombre?: string
  descripcion?: string
  estado?: ProyectoEstado
  fecha_inicio?: string
  fecha_fin?: string
  presupuesto?: number
}

export interface ProyectoListResponse {
  items: Proyecto[]
  total: number
}

export interface Asignacion {
  id: string
  proyecto_id: string
  empleado_id: string
  empleado_nombre: string | null
  empleado_empresa_id: string
  empleado_empresa_nombre: string | null
  rol: string
  valor_hora: number
  fecha_desde: string | null
  fecha_hasta: string | null
  activo: boolean
  created_at: string
}

export interface AsignacionCreate {
  empleado_id: string
  rol: string
  valor_hora: number
  fecha_desde?: string
  fecha_hasta?: string
}

export interface AsignacionUpdate {
  rol?: string
  valor_hora?: number
  fecha_desde?: string
  fecha_hasta?: string
  activo?: boolean
}

export interface AsignacionListResponse {
  items: Asignacion[]
  total: number
}

export interface AsignacionBulkCreate {
  empleado_ids: string[]
  rol: string
  valor_hora: number
  fecha_desde?: string
  fecha_hasta?: string
}

export interface AsignacionAreaCreate {
  area_id: string
  rol: string
  valor_hora: number
  fecha_desde?: string
  fecha_hasta?: string
}

export interface AsignacionBulkResult {
  asignados: Asignacion[]
  /**
   * Ya estaban en el proyecto. NO son errores: es la operación siendo idempotente.
   *
   * Van aparte desde que existe el alta por área, donde lo normal es que la mitad del área ya
   * esté asignada — "15 errores" se leería como un fallo masivo. Antes el mensaje del modal
   * tenía que aclararlo a mano ("ya asignados o inactivos") porque el tipo no los distinguía.
   */
  ya_asignados: { empleado_id: string; motivo: string }[]
  /** Fallos DE VERDAD: el empleado no existe, o está dado de baja. */
  errores: { empleado_id: string; motivo: string }[]
}

export interface Hora {
  id: string
  asignacion_id: string
  proyecto_id: string
  empleado_nombre: string | null
  empleado_empresa_nombre: string | null
  fecha: string
  horas: number
  valor_hora_snapshot: number
  costo: number
  descripcion: string | null
  created_at: string
}

export interface HoraCreate {
  asignacion_id: string
  fecha: string
  horas: number
  descripcion?: string
}

export interface HoraListResponse {
  items: Hora[]
  total: number
}
