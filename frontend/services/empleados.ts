import type {
  Empleado, EmpleadoCreate, EmpleadoListResponse, EmpleadoSeleccionable, EmpleadoUpdate,
} from "@/types/empleado"
import { apiFetch, descargarArchivo, type FormatoExport } from "@/services/api"

/**
 * Filtros del listado de empleados, compartidos por `fetchEmpleados` y `exportarEmpleados`
 * con los MISMOS nombres a propósito: antes eran cuatro posicionales `string | undefined`
 * en distinto orden entre las dos, así que copiar argumentos de una a la otra compilaba
 * igual y mandaba el filtro equivocado al backend.
 *
 * `empresaId` viaja por header `X-Empresa-Id` (el valor "todas" el backend lo interpreta
 * como consolidado); el resto van como query params.
 *
 * `esLider` es un booleano de tres estados: `undefined` = sin filtro, `true` = solo líderes,
 * `false` = solo no-líderes. Por eso NO se puede normalizar con `|| undefined` como los
 * strings: `false` es un filtro válido, no un vacío.
 */
export interface EmpleadosFiltros {
  search?: string
  estado?: string
  empresaId?: string
  areaId?: string
  esLider?: boolean
}

export async function fetchEmpleados(
  opts: EmpleadosFiltros & { page: number; pageSize: number },
): Promise<EmpleadoListResponse> {
  const { page, pageSize, search, estado, empresaId, areaId, esLider } = opts
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  if (search) params.set("search", search)
  if (estado) params.set("estado", estado)
  if (areaId) params.set("area_id", areaId)
  if (esLider !== undefined) params.set("es_lider", String(esLider))
  return apiFetch<EmpleadoListResponse>(
    `/api/empleados?${params}`,
    empresaId ? { headers: { "X-Empresa-Id": empresaId } } : {},
  )
}

/** Exporta el listado de empleados (pdf/excel/csv/word) con los filtros activos aplicados. */
export function exportarEmpleados(
  opts: EmpleadosFiltros & { formato: FormatoExport },
): Promise<void> {
  const { formato, search, estado, empresaId, areaId, esLider } = opts
  const headers = empresaId ? { "X-Empresa-Id": empresaId } : undefined
  return descargarArchivo("/api/empleados/exportar", formato, "empleados", headers, {
    search,
    estado,
    area_id: areaId,
    es_lider: esLider === undefined ? undefined : String(esLider),
  })
}

export async function fetchEmpleado(id: string): Promise<Empleado> {
  return apiFetch<Empleado>(`/api/empleados/${id}`)
}

export async function createEmpleado(data: EmpleadoCreate): Promise<Empleado> {
  return apiFetch<Empleado>("/api/empleados", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function updateEmpleado(id: string, data: EmpleadoUpdate): Promise<Empleado> {
  return apiFetch<Empleado>(`/api/empleados/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  })
}

export async function fetchRolesConocidos(): Promise<string[]> {
  return apiFetch<string[]>("/api/empleados/roles-conocidos")
}

export async function fetchValoresConocidos(campo: string): Promise<string[]> {
  return apiFetch<string[]>(`/api/empleados/valores-conocidos?campo=${encodeURIComponent(campo)}`)
}

export async function fetchEmpleadosSeleccionables(
  empresaId: string,
): Promise<EmpleadoSeleccionable[]> {
  return apiFetch<EmpleadoSeleccionable[]>(
    `/api/empleados/seleccionables?empresa_id=${encodeURIComponent(empresaId)}`,
  )
}
