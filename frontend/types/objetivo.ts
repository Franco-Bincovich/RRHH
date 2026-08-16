export type EstadoObjetivo  = "por_hacer" | "haciendo" | "terminado"
export type PrioridadObjetivo = "baja" | "media" | "alta"

/** Un responsable del objetivo (tabla puente objetivo_responsables, migración 096). */
export interface ResponsableItem {
  id: string
  nombre: string | null
}

export interface Objetivo {
  id: string
  empresa_id: string
  empresa_nombre: string | null
  responsable_id: string
  responsable_nombre: string | null
  titulo: string
  descripcion: string | null
  prioridad: PrioridadObjetivo
  estado: EstadoObjetivo
  fecha_entrega: string | null  // "YYYY-MM-DD"
  created_at: string
  updated_at: string
  /** null = objetivo raíz. La jerarquía admite dos niveles (migración 095). */
  parent_id: string | null
  /** Derivado del padre: alimenta la columna "Objetivo padre" del export. */
  parent_titulo: string | null
  /** Lista COMPLETA, el dueño incluido. */
  responsables: ResponsableItem[]
  /** Subobjetivos. Siempre vacía en un hijo: la profundidad máxima es 2. */
  hijos: Objetivo[]
}

export interface ObjetivoCreate {
  empresa_id: string
  responsable_id: string
  titulo: string
  descripcion?: string
  prioridad: PrioridadObjetivo
  fecha_entrega?: string
  parent_id?: string
  /** Responsables ADICIONALES al dueño; el backend agrega al dueño siempre. */
  responsables?: string[]
}

export interface ObjetivoUpdate {
  responsable_id?: string
  titulo?: string
  descripcion?: string
  prioridad?: PrioridadObjetivo
  fecha_entrega?: string
  parent_id?: string
  responsables?: string[]
}

export interface CambiarEstadoRequest {
  estado: EstadoObjetivo
}

export interface ObjetivoListResponse {
  items: Objetivo[]
  /**
   * 🔴 HOY `total === items.length` porque este listado NO pagina: el backend devuelve todo.
   * El día que pagine (sesiones 2–5), `total` pasa a ser "cuántas hay" y `items` una página.
   * Un contador escrito como `items.length` va a seguir compilando y va a decir 20 sobre 400.
   * Usá `total` para contar y `items` sólo para recorrer.
   */
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface UserItem {
  id: string
  nombre: string
  apellido: string
  email: string
  rol: string
}
