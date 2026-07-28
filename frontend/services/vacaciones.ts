import type {
  SaldoVacaciones,
  SolicitudVacaciones,
  SolicitudVacacionesCreate,
  SolicitudVacacionesListResponse,
} from "@/types/vacaciones"
import { apiFetch, descargarArchivo, type FormatoExport } from "@/services/api"

/**
 * Filtros del listado de vacaciones. Los consumen el listado Y el export: es el mismo tipo a
 * propósito, para que un filtro nuevo no pueda quedar en uno solo de los dos.
 *
 * `fechaDesde`/`fechaHasta` acotan por SOLAPAMIENTO con el rango, no por contención: una
 * solicitud que empieza antes del rango pero lo cruza ENTRA. La semántica vive en el backend
 * (repositories/_rango_fechas.py) y acá no se reimplementa nada — el filtro es server-side.
 */
export interface VacacionesFiltros {
  empresaIdOverride?: string
  areaId?: string
  empleadoId?: string
  estado?: string
  fechaDesde?: string
  fechaHasta?: string
  /** Empleados asignados a ese proyecto (semántica en el backend, _scope_filtros). */
  proyectoId?: string
}

/** Traducción filtros → query params. Fuente ÚNICA compartida por listado y export. */
function queryVacaciones(f: VacacionesFiltros): Record<string, string | undefined> {
  return {
    area_id: f.areaId,
    empleado_id: f.empleadoId,
    estado: f.estado,
    fecha_desde: f.fechaDesde,
    fecha_hasta: f.fechaHasta,
    proyecto_id: f.proyectoId,
  }
}

export async function fetchVacaciones(
  filtros: VacacionesFiltros = {},
  page = 1,
  pageSize = 20,
): Promise<SolicitudVacacionesListResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  for (const [k, v] of Object.entries(queryVacaciones(filtros))) {
    if (v) params.set(k, v)
  }
  return apiFetch<SolicitudVacacionesListResponse>(
    `/api/vacaciones?${params}`,
    filtros.empresaIdOverride ? { headers: { "X-Empresa-Id": filtros.empresaIdOverride } } : {},
  )
}

/** Lista las vacaciones (no canceladas) de un empleado, para su ficha. Endpoint dedicado. */
export async function fetchVacacionesEmpleado(
  empleadoId: string,
): Promise<SolicitudVacacionesListResponse> {
  return apiFetch<SolicitudVacacionesListResponse>(`/api/vacaciones/empleado/${empleadoId}`)
}

export async function fetchVacacion(id: string): Promise<SolicitudVacaciones> {
  return apiFetch<SolicitudVacaciones>(`/api/vacaciones/${id}`)
}

export async function createVacacion(
  data: SolicitudVacacionesCreate,
): Promise<SolicitudVacaciones> {
  return apiFetch<SolicitudVacaciones>("/api/vacaciones", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function cancelarVacacion(id: string): Promise<SolicitudVacaciones> {
  return apiFetch<SolicitudVacaciones>(`/api/vacaciones/${id}/cancelar`, {
    method: "PUT",
  })
}

export async function fetchSaldoVacaciones(
  empleadoId: string,
  empresaIdOverride?: string,
): Promise<SaldoVacaciones> {
  return apiFetch<SaldoVacaciones>(
    `/api/vacaciones/saldo/${empleadoId}`,
    empresaIdOverride ? { headers: { "X-Empresa-Id": empresaIdOverride } } : {},
  )
}

/** Exporta el listado de vacaciones con los MISMOS filtros que el listado. */
export function exportarVacaciones(
  formato: FormatoExport,
  filtros: VacacionesFiltros = {},
): Promise<void> {
  const headers = filtros.empresaIdOverride ? { "X-Empresa-Id": filtros.empresaIdOverride } : undefined
  return descargarArchivo("/api/vacaciones/exportar", formato, "vacaciones", headers, queryVacaciones(filtros))
}
