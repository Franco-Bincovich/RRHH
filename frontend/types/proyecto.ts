/** Vocabulario cerrado de la modalidad del dia. Espejo del CHECK de la migracion 103. */
export type Modalidad = "home_office" | "on_site"

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

/**
 * Una fila de `horas_proyecto`. Espejo de `backend/schemas/horas.py::HoraResponse`.
 *
 * 🔴 DESDE LA MIGRACIÓN 103 HAY DOS FORMAS DE FILA, y por eso casi todo es nullable:
 *   · CAMINO VIEJO (POST /api/proyectos/{id}/horas): asignación + proyecto + snapshot.
 *   · CARGA DIRECTA (link público de horas): cliente + modalidad + textos, SIN asignación,
 *     SIN proyecto y SIN `valor_hora_snapshot` — o sea sin nada con qué costear.
 *
 * `costo` es `number | null` y NO `number`: null significa "no se puede costear", que no es lo
 * mismo que "costó cero" (mismo criterio que `CosteoResumen.pct_consumido`). Quedó anotado como
 * pendiente al crear el modelo; se corrige acá. Todo lo que formatee `costo` tiene que
 * contemplar el null — un `ARS.format(null)` imprime "$ NaN".
 */
export interface Hora {
  id: string
  empresa_id: string | null
  asignacion_id: string | null
  proyecto_id: string | null
  empleado_id: string | null
  empleado_nombre: string | null
  empleado_empresa_nombre: string | null
  fecha: string
  horas: number
  valor_hora_snapshot: number | null
  costo: number | null
  descripcion: string | null
  cliente_id: string | null
  cliente_nombre: string | null
  modalidad: Modalidad | null
  proyecto_texto: string | null
  tarea_texto: string | null
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
  /**
   * 🔴 Totales de TODAS las cargas del proyecto, no de `items`.
   *
   * `items` es una página. Sumarla con un `.reduce()` daba el total de lo que se ve presentado
   * como el total del proyecto: con 400 cargas la pantalla decía "9 h", y el número cambiaba al
   * pasar de página. Los calcula el backend sobre el conjunto completo.
   *
   * REGLA DEL MOLDE: si un listado pagina, todo agregado sobre él viene del backend. Un total
   * derivado de la página es correcto solo mientras la página sea todo — o sea, hasta que
   * alguien agregue paginación, que es justo cuando nadie vuelve a mirar el `.reduce()`.
   */
  total_horas: number
  /** Las cargas sin `valor_hora_snapshot` suman 0 acá (ver `Hora.costo`): para un TOTAL "no
   *  costeable" aporta cero. Eso NO habilita imprimir "$ 0" fila por fila. */
  total_costo: number
}
