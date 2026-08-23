export type EstadoObjetivo  = "por_hacer" | "haciendo" | "terminado"

/**
 * LAS DOS VISTAS del módulo (migración 119): un objetivo pertenece a UNA y no se comparte.
 * `anual` es la que Capital Humano le presenta al directorio; `operativo` acepta cualquier
 * expresión de tiempo. Espejo del `Literal` de `backend/schemas/objetivo.py`.
 *
 * 🔴 EL TIPO SE ESCRIBE ACÁ; LAS ETIQUETAS NO. Los dos literales son a la vez el CHECK de la base
 * y el `Literal` de Pydantic, así que tienen que existir como tipo para que `tsc` valide la URL
 * que se arma. Lo que NO se hardcodea es el par value→label del selector: eso viene de
 * `GET /api/objetivos/campos` (ver `fetchCamposObjetivo`), que es la regla que ese endpoint
 * existe para sostener.
 */
export type TipoObjetivo = "anual" | "operativo"
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
  /** A cuál de las dos vistas pertenece. Requerido, como en el backend: no tiene valor neutro. */
  tipo: TipoObjetivo
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
  /** Opcional: sin esto el backend aplica su `TIPO_POR_DEFECTO` ("operativo"), que es lo decidido. */
  tipo?: TipoObjetivo
}

export interface ObjetivoUpdate {
  responsable_id?: string
  titulo?: string
  descripcion?: string
  prioridad?: PrioridadObjetivo
  fecha_entrega?: string
  parent_id?: string
  responsables?: string[]
  /** `undefined` = no se toca la vista. Es una columna editable, no una marca de nacimiento. */
  tipo?: TipoObjetivo
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
