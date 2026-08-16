import { API_BASE, apiFetch, authHeaders, descargarArchivo, type FormatoExport } from "@/services/api"
import type {
  Asignacion,
  AsignacionCreate,
  AsignacionListResponse,
  AsignacionUpdate,
  Capacitacion,
  CapacitacionCreate,
  CapacitacionListResponse,
  CapacitacionUpdate,
} from "@/types/capacitacion"

const BASE = "/api/capacitaciones"
const BASE_AS = `${BASE}/asignaciones`

// ── Catálogo ──────────────────────────────────────────────────────────────────

/** Traducción filtros → query params del catálogo. Fuente ÚNICA: la usan el listado y el export. */
function queryCatalogo(soloActivos: boolean): Record<string, string> {
  return { solo_activos: String(soloActivos) }
}

export async function fetchCapacitaciones(
  empresaIdOverride?: string,
  soloActivos = true,
): Promise<CapacitacionListResponse> {
  const q = new URLSearchParams(queryCatalogo(soloActivos))
  return apiFetch<CapacitacionListResponse>(
    `${BASE}?${q}`,
    empresaIdOverride ? { headers: { "X-Empresa-Id": empresaIdOverride } } : {},
  )
}

/**
 * Exporta el CATÁLOGO con el MISMO filtro que la pantalla.
 *
 * 🔴 SE LLAMA `exportarCatalogoCapacitaciones`, NO `exportarCapacitaciones`: ese nombre ya lo usa
 * el export de ASIGNACIONES (más abajo). Son dos listados distintos, en dos pestañas distintas y
 * con dos endpoints distintos — el catálogo dice qué cursos existen, las asignaciones quién hizo
 * cuál. El archivo baja con nombre "catalogo-capacitaciones" por el mismo motivo.
 *
 * 🔴 `soloActivos` viaja por la misma `queryCatalogo` que el listado: sin él, el archivo traería
 * las capacitaciones inactivas que la tabla está ocultando. Es el bug exacto que la invariante
 * list↔export existe para evitar, y acá era posible porque este listado SÍ tiene un filtro
 * (el checkbox "Solo activos").
 */
export function exportarCatalogoCapacitaciones(
  formato: FormatoExport,
  empresaIdOverride?: string,
  soloActivos = true,
): Promise<void> {
  return descargarArchivo(
    `${BASE}/exportar`, formato, "catalogo-capacitaciones",
    empresaIdOverride ? { "X-Empresa-Id": empresaIdOverride } : undefined,
    queryCatalogo(soloActivos),
  )
}

export async function createCapacitacion(data: CapacitacionCreate): Promise<Capacitacion> {
  return apiFetch<Capacitacion>(BASE, { method: "POST", body: JSON.stringify(data) })
}

export async function updateCapacitacion(id: string, data: CapacitacionUpdate): Promise<Capacitacion> {
  return apiFetch<Capacitacion>(`${BASE}/${id}`, { method: "PUT", body: JSON.stringify(data) })
}

export async function deleteCapacitacion(id: string): Promise<void> {
  await apiFetch<{ ok: boolean }>(`${BASE}/${id}`, { method: "DELETE" })
}

// ── Asignaciones ──────────────────────────────────────────────────────────────

/**
 * Filtros del listado de asignaciones de capacitación.
 * Los consumen el listado Y el export: es el mismo tipo a propósito, para que un filtro
 * nuevo no pueda quedar en uno solo de los dos (invariante list ↔ export).
 */
export interface AsignacionesCapacitacionFiltros {
  empresaIdOverride?: string
  empleadoId?: string
  capacitacionId?: string
  estado?: string
  areaId?: string
}

/**
 * Traduce los filtros a query params del backend. Fuente ÚNICA de esa traducción: el listado
 * y el export la comparten, así que no pueden mandar cosas distintas. Si se suma un filtro,
 * se suma acá una sola vez y le llega a los dos.
 */
function queryAsignaciones(f: AsignacionesCapacitacionFiltros): Record<string, string | undefined> {
  return {
    empleado_id: f.empleadoId,
    capacitacion_id: f.capacitacionId,
    estado: f.estado,
    area_id: f.areaId,
  }
}

function headersEmpresa(empresaIdOverride?: string): Record<string, string> | undefined {
  return empresaIdOverride ? { "X-Empresa-Id": empresaIdOverride } : undefined
}

export async function fetchAsignaciones(
  params: AsignacionesCapacitacionFiltros, page = 1, pageSize = 20,
): Promise<AsignacionListResponse> {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(queryAsignaciones(params))) {
    if (v) q.set(k, v)
  }
  // `page`/`page_size` van aparte de la traducción compartida con el export: el export no se
  // pagina, y colarlos ahí haría que el archivo saliera con una página en vez del listado.
  q.set("page", String(page))
  q.set("page_size", String(pageSize))
  const query = q.size ? `?${q}` : ""
  return apiFetch<AsignacionListResponse>(
    `${BASE_AS}${query}`,
    params.empresaIdOverride ? { headers: { "X-Empresa-Id": params.empresaIdOverride } } : {},
  )
}

export async function createAsignacion(data: AsignacionCreate): Promise<Asignacion> {
  return apiFetch<Asignacion>(BASE_AS, { method: "POST", body: JSON.stringify(data) })
}

export async function updateAsignacion(id: string, data: AsignacionUpdate): Promise<Asignacion> {
  return apiFetch<Asignacion>(`${BASE_AS}/${id}`, { method: "PUT", body: JSON.stringify(data) })
}

export async function deleteAsignacion(id: string): Promise<void> {
  await apiFetch<{ ok: boolean }>(`${BASE_AS}/${id}`, { method: "DELETE" })
}

export async function uploadCertificado(id: string, file: File): Promise<Asignacion> {
  const form = new FormData()
  form.append("file", file)
  const headers = authHeaders()
  delete headers["Content-Type"]
  const res = await fetch(`${API_BASE}${BASE_AS}/${id}/certificado`, {
    method: "POST",
    headers,
    body: form,
  })
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { message?: string }
    throw new Error(body.message ?? "Error al subir el certificado")
  }
  return res.json() as Promise<Asignacion>
}

export async function getCertificadoUrl(id: string): Promise<string> {
  const data = await apiFetch<{ url: string }>(`${BASE_AS}/${id}/certificado`)
  return data.url
}

// ── Export ────────────────────────────────────────────────────────────────────

/**
 * Exporta el listado de asignaciones de capacitación (pdf/excel/csv/word) vía el motor central.
 * Toma los MISMOS filtros que `fetchAsignaciones` y los traduce con la misma función, así que
 * lo que se descarga es exactamente lo que se está viendo.
 */
export function exportarCapacitaciones(
  formato: FormatoExport,
  filtros: AsignacionesCapacitacionFiltros = {},
): Promise<void> {
  return descargarArchivo(
    "/api/capacitaciones/asignaciones/exportar", formato, "capacitaciones",
    headersEmpresa(filtros.empresaIdOverride), queryAsignaciones(filtros),
  )
}
