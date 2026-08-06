// ── Vista por empresa: GET /api/organigrama ───────────────────────────────────

export interface EmpleadoNodoAPI {
  id: string
  nombre: string
  apellido: string
  cargo: string | null
  avatar_url: string | null
}

export interface AreaNodoAPI {
  id: string
  nombre: string
  responsable: EmpleadoNodoAPI | null
  empleados: EmpleadoNodoAPI[]
  total_empleados: number
}

export interface EmpresaNodoAPI {
  id: string
  nombre: string
  total_empleados: number
  areas: AreaNodoAPI[]
}

// ── Vistas por proyecto: GET /api/organigrama/proyectos ───────────────────────

export interface EmpleadoProyectoNodoAPI {
  id: string
  nombre: string
  apellido: string
  iniciales: string
  cargo: string | null
  rol: string
  empleado_empresa_id: string
  empleado_empresa_nombre: string | null
  total_proyectos: number
  /**
   * Contrato de la asignación. Los tres llegan vacíos hoy (las 31 asignaciones de producción
   * tienen valor_hora 0 y las dos fechas en null).
   *
   * `valor_hora` NO es opcional en la API —la columna es NOT NULL DEFAULT 0— pero un 0
   * significa "no está cargado", no "cobra cero": la traducción la hace `contratoAsignacion.ts`.
   * Las fechas son columnas `date`, o sea ISO de solo fecha ("2026-03-01").
   */
  valor_hora: number
  fecha_desde: string | null
  fecha_hasta: string | null
}

export interface ProyectoOrgNodoAPI {
  id: string
  nombre: string
  estado: string
  empresa_id: string
  empresa_nombre: string | null
  total_asignados: number
  empleados: EmpleadoProyectoNodoAPI[]
}

export interface EmpresaLeyendaAPI {
  id: string
  nombre: string
}

export interface OrgProyectosResponse {
  proyectos: ProyectoOrgNodoAPI[]
  empresas_orden: EmpresaLeyendaAPI[]
}
