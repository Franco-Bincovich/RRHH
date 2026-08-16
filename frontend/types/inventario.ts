export type EstadoItem = "disponible" | "asignado" | "en_reparacion" | "baja"
export type EstadoDevolucion = "ok" | "con_daño"

export interface InventarioItem {
  id: string
  empresa_id: string
  empresa_nombre: string | null
  nombre: string
  tipo: string
  descripcion: string | null
  numero_serie: string | null
  estado: EstadoItem
  fecha_alta: string   // "YYYY-MM-DD"
  costo: number | null
  notas: string | null
  asignado_a: string | null  // nombre del empleado que lo tiene actualmente
  created_at: string
}

export interface InventarioItemCreate {
  empresa_id: string
  nombre: string
  tipo: string
  descripcion?: string
  numero_serie?: string
  costo?: number
  notas?: string
}

export interface InventarioItemUpdate {
  nombre?: string
  tipo?: string
  descripcion?: string
  numero_serie?: string
  costo?: number
  notas?: string
}

export interface ItemListResponse {
  items: InventarioItem[]
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

export interface Asignacion {
  id: string
  empresa_id: string
  empresa_nombre: string | null
  item_id: string
  item_nombre: string | null
  item_tipo: string | null
  item_numero_serie: string | null
  empleado_id: string
  empleado_nombre: string | null
  fecha_asignacion: string   // "YYYY-MM-DD"
  fecha_devolucion: string | null
  estado_devolucion: EstadoDevolucion | null
  notas: string | null
  created_at: string
}

export interface AsignacionCreate {
  item_id: string
  empleado_id: string
}

export interface DevolucionRequest {
  estado_devolucion: EstadoDevolucion
  notas?: string
}

export interface AsignacionListResponse {
  items: Asignacion[]
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
