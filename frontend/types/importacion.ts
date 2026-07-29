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

export interface ImportacionNominaEmpleadosResult {
  total: number
  creados: number       // altas nuevas (DNI no existía)
  actualizados: number  // updates (DNI ya existía) — dedup
  cargados_ok: number   // cargados sin faltantes
  con_faltantes: FilaConFaltantes[]
  no_cargados: FilaNoCargada[]
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
