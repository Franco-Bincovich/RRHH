// ─── Comunes ────────────────────────────────────────────────────────────────

export interface FilaError {
  fila: number
  campo: string
  error: string
}

export interface ConfirmarError {
  fila: number
  error: string
}

// ─── Nómina de empleados (roster, 27 columnas) ──────────────────────────────

export interface FilaConFaltantes {
  fila: number
  empleado: string
  faltan: string[]
}

export interface FilaNoCargada {
  fila: number
  empleado: string
  motivo: string
}

/**
 * Fila que SÍ se cargó pero cuyo superior no se pudo asignar. NO es una fila perdida: el
 * empleado quedó bien, lo único que falta es el `manager_id`. `superior` es el texto crudo del
 * CSV — es lo que un humano necesita ver para saber a quién apuntaba.
 */
export interface SuperiorPendiente {
  fila: number
  empleado: string
  superior: string
  motivo: string
}

export interface ImportacionNominaEmpleadosResult {
  total: number
  creados: number       // altas nuevas (DNI no existía)
  actualizados: number  // updates (DNI ya existía) — dedup
  cargados_ok: number   // cargados sin faltantes
  con_faltantes: FilaConFaltantes[]
  no_cargados: FilaNoCargada[]
  /** Superiores del CSV que se resolvieron a manager_id en la segunda pasada del import. */
  superiores_resueltos: number
  /** Los que no: quedan guardados y se pueden resolver después sin re-subir el archivo. */
  superiores_pendientes: SuperiorPendiente[]
  /**
   * El archivo NO se terminó de procesar: se agotó el presupuesto de tiempo del backend.
   * NO es un error — lo procesado quedó cargado y reintentar con el MISMO archivo continúa
   * donde quedó (el dedup por DNI manda las ya cargadas por la rama de update).
   */
  parcial: boolean
  ultima_fila_procesada: number | null   // nº de fila del CSV (el encabezado es la 1)
  filas_sin_procesar: number
  segundos: number | null                // tiempo que consumió el backend
}

// ─── Nómina de sueldos (costos_nomina) ──────────────────────────────────────

export interface FilaNominaPreview {
  fila: number
  dni: string
  nombre_empleado: string
  empleado_id: string
  anio: number
  mes: number
  salario_bruto: number
  neto: number
  es_actualizacion: boolean
}

export interface ImportacionNominaPreview {
  filas_validas: FilaNominaPreview[]
  errores: FilaError[]
}

export interface ImportacionNominaResult {
  importados: number
  actualizados: number
  errores: ConfirmarError[]
}

// ─── Superiores pendientes de resolver (migración 086) ──────────────────────

/**
 * Un empleado cuyo superior el import no pudo resolver. `empleado` se resuelve contra la tabla
 * de empleados al leer (no está duplicado en la fila), así que si lo renombran, esto lo refleja.
 */
export interface SuperiorPendienteItem {
  empleado_id: string
  empleado: string
  superior: string
  motivo: string
}

export interface SuperioresPendientesListResponse {
  items: SuperiorPendienteItem[]
  total: number
}

/**
 * Resultado de reintentar. `pendientes` son los que SIGUEN sin resolverse, con el motivo de
 * AHORA — que puede no ser el del import: dar de alta a un homónimo convierte un "no hay ningún
 * empleado con ese nombre" en un "hay 2, elegí cuál".
 */
export interface ResolucionPendientesResult {
  resueltos: number
  pendientes: SuperiorPendienteItem[]
}
