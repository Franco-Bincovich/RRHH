export interface TipoAusencia {
  id: string
  nombre: string
  /** Los 4 tipos base no se pueden dar de baja: son el vocabulario mínimo del histórico. */
  es_base: boolean
  activo: boolean
  /** Migración 085. null = tipo global, disponible para todas las empresas. */
  empresa_id: string | null
  /**
   * Si las ausencias de este tipo entran en la tasa de ausentismo.
   *
   * NO reemplaza a `Ausencia.justificada`: son preguntas distintas. `justificada` es un HECHO
   * de la instancia ("¿esta vez trajo certificado?"); esto es una POLÍTICA del tipo
   * ("¿maternidad computa como ausentismo?"). Una licencia puede estar justificada y aun así
   * no computar.
   */
  cuenta_ausentismo: boolean
}

/** Campos editables de un tipo. Todo opcional: es un PATCH, se manda solo lo que cambia. */
export interface TipoAusenciaUpdate {
  nombre?: string
  /** `false` es la BAJA. No hay borrado: rompería la FK de las ausencias históricas. */
  activo?: boolean
  cuenta_ausentismo?: boolean
}

export interface TipoAusenciaListResponse {
  items: TipoAusencia[]
  total: number
}

export interface Ausencia {
  id: string
  empresa_id: string
  empresa_nombre: string | null
  empleado_id: string
  empleado_nombre: string | null
  area_id: string | null
  area_nombre: string | null
  tipo_id: string
  tipo_nombre: string | null
  fecha_desde: string  // ISO "YYYY-MM-DD"
  fecha_hasta: string
  dias: number
  justificada: boolean
  motivo: string | null
  created_at: string
}

export interface AusenciaCreate {
  empleado_id: string
  tipo_id: string
  fecha_desde: string
  fecha_hasta: string
  justificada: boolean
  motivo?: string
}

export interface AusenciaUpdate {
  tipo_id?: string
  fecha_desde?: string
  fecha_hasta?: string
  justificada?: boolean
  motivo?: string
}

export interface AusenciaListResponse {
  items: Ausencia[]
  total: number
}
