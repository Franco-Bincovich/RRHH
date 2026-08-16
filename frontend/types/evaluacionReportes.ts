// Tipos de los reportes de resultados de evaluaciones. Espejo de schemas/evaluacion_reportes.py.

export interface LoteEvaluacion {
  id: string
  empresa_id: string
  periodo: string
  importado_por: string | null
  created_at: string
  empresa_nombre: string | null
  importado_por_nombre: string | null
  evaluados: number
}

export interface LotesResponse {
  items: LoteEvaluacion[]
  total: number
}

export interface LoteBulkError {
  id: string
  motivo: string
}

export interface LotesBulkResult {
  eliminados: string[]
  fallidos: LoteBulkError[]
}

export interface ResumenCiclo {
  evaluados: number
  con_nota_final: number
  promedio: number | null
  nota_mas_alta: number | null
  nota_mas_baja: number | null
  evaluaciones: number
}

export interface BrechaItem {
  empleado_id: string | null
  apellido: string
  nombre: string
  auto: number | null
  terceros: number | null
  brecha: number | null
}

export interface SectorItem {
  sector: string
  evaluados: number
  promedio: number
  minima: number
  maxima: number
}

export interface CompetenciaItem {
  competencia: string
  promedio: number
  n: number
}

export interface CompetenciasReporte {
  lider: CompetenciaItem[]
  general: CompetenciaItem[]
  n_lider: number
  n_general: number
}

export interface MetricasResponse {
  resumen: ResumenCiclo
  brecha: BrechaItem[]
  sectores: SectorItem[]
  competencias: CompetenciasReporte
}

export interface EvaluadoListadoItem {
  id: string
  empleado_id: string | null
  apellido: string
  nombre: string
  sector: string | null
  superior: string | null
  tipos: string[]
  perfil: string
  nota_final: number | null
  asignado: boolean
}

export interface EvaluadoListadoResponse {
  items: EvaluadoListadoItem[]
  /** Total del FILTRO sin paginar (`count="exact"`), no el largo de `items`. */
  total: number
  page: number
  page_size: number
  total_pages: number
  /**
   * 🔴 LOS SECTORES DEL LOTE ENTERO, no los de la página. El desplegable se poblaba con
   * `new Set(todos.map(e => e.sector))` sobre lo traído: al paginar ofrecería sólo los
   * sectores que aparecen en la página 1, y filtrar por cualquier otro sería imposible —
   * el usuario ni siquiera vería la opción.
   */
  sectores: string[]
}

export interface FichaResponse {
  apellido: string
  nombre: string
  sector: string | null
  perfil: string
  nota_final: number | null
  competencias: string[]
  tipos: string[]
  celdas: Record<string, Record<string, number>>
  promedio_terceros: Record<string, number>
}
