// 🔴 `entidad_capacitadora`, `modalidad` y `tipo` son string LIBRE, sin union de literales, a
// propósito: las columnas son text sin CHECK (mig 116) y el vocabulario real no se conoce — el
// Excel trae UN solo valor de cada una. Angostar el tipo acá inventaría un contrato que el
// backend y la base no tienen. Espejo del mismo comentario en schemas/capacitacion.py.
export interface Capacitacion {
  id: string
  empresa_id: string
  empresa_nombre: string | null
  nombre: string
  descripcion: string | null
  categoria: string | null
  duracion_horas: number | null
  entidad_capacitadora: string | null
  modalidad: string | null
  tipo: string | null
  obligatoria: boolean
  activo: boolean
  created_at: string
}

export interface CapacitacionCreate {
  empresa_id: string
  nombre: string
  descripcion?: string
  categoria?: string
  duracion_horas?: number
  entidad_capacitadora?: string
  modalidad?: string
  tipo?: string
  obligatoria: boolean
}

export interface CapacitacionUpdate {
  nombre?: string
  descripcion?: string
  categoria?: string
  duracion_horas?: number
  entidad_capacitadora?: string
  modalidad?: string
  tipo?: string
  obligatoria?: boolean
  activo?: boolean
}

export interface CapacitacionListResponse {
  items: Capacitacion[]
  total: number
}

export interface Asignacion {
  id: string
  empresa_id: string
  empresa_nombre: string | null
  capacitacion_id: string
  capacitacion_nombre: string | null
  // 🔴 null = fila de nombre libre (migración 116): la formación de alguien que el import no
  // matcheó contra el padrón, o de alguien que ya no trabaja acá. `nombre_libre` es el nombre
  // crudo del Excel y es lo único que identifica a esa persona.
  // `empleado_id === null` ES el "no está vinculado": no hay flag booleano aparte a propósito,
  // porque dos formas de decir lo mismo divergen (evaluaciones manda `asignado` Y `empleado_id`).
  empleado_id: string | null
  empleado_nombre: string | null
  nombre_libre: string | null
  area_id: string | null
  area_nombre: string | null
  // ⚠️ `anio` y `mes` son string, no number: las columnas son TEXT (mig 116) porque el Excel
  // los trae a mano y sin normalizar ("2026", "marzo"/"Marzo"). No parsearlos.
  proyecto: string | null
  anio: string | null
  mes: string | null
  estado: "pendiente" | "en_curso" | "completado"
  fecha_asignacion: string | null   // "YYYY-MM-DD"
  fecha_limite: string | null
  fecha_completado: string | null
  certificado_url: string | null    // storage path (privado) — usar signed URL para descargar
  created_at: string
}

export interface AsignacionCreate {
  capacitacion_id: string
  // ⚠️ Acá SIGUE siendo obligatorio, al revés que en `Asignacion`. Asignar un curso desde la
  // pantalla exige elegir un colaborador: el backend resuelve la empresa a partir de él
  // (`AsignacionCreate.empleado_id: UUID` en schemas/capacitacion.py) y sin él responde 422.
  // Las filas de nombre libre nacen del import, que no pasa por este endpoint.
  empleado_id: string
  fecha_asignacion?: string
  fecha_limite?: string
  proyecto?: string
  anio?: string
  mes?: string
  nombre_libre?: string
}

export interface AsignacionUpdate {
  estado?: "pendiente" | "en_curso" | "completado"
  fecha_limite?: string
  fecha_completado?: string
  proyecto?: string
  anio?: string
  mes?: string
  nombre_libre?: string
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
