export interface Capacitacion {
  id: string
  empresa_id: string
  empresa_nombre: string | null
  nombre: string
  descripcion: string | null
  categoria: string | null
  duracion_horas: number | null
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
  obligatoria: boolean
}

export interface CapacitacionUpdate {
  nombre?: string
  descripcion?: string
  categoria?: string
  duracion_horas?: number
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
}

export interface AsignacionUpdate {
  estado?: "pendiente" | "en_curso" | "completado"
  fecha_limite?: string
  fecha_completado?: string
}

export interface AsignacionListResponse {
  items: Asignacion[]
  total: number
}
