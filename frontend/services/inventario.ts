import type {
  Asignacion, AsignacionCreate, AsignacionListResponse,
  DevolucionRequest, InventarioItem, InventarioItemCreate, InventarioItemUpdate,
  ItemListResponse,
} from "@/types/inventario"
import { apiFetch, descargarArchivo, type FormatoExport } from "@/services/api"

const ITEMS  = "/api/inventario/items"
const ASIG   = "/api/inventario/asignaciones"

function override(empresaId?: string): RequestInit {
  return empresaId ? { headers: { "X-Empresa-Id": empresaId } } : {}
}

/**
 * Filtros de los dos listados de inventario. Los consumen el listado Y el export: es el mismo
 * tipo a propósito, para que un filtro nuevo no pueda quedar en uno solo de los dos
 * (invariante list ↔ export).
 */
export interface ItemsFiltros { empresaIdOverride?: string; estado?: string }
export interface AsignacionesInventarioFiltros { empresaIdOverride?: string; empleadoId?: string }

/**
 * Traducción filtros → query params. Fuente ÚNICA compartida por listado y export: si se suma
 * un filtro, se suma acá una sola vez y le llega a los dos.
 */
function queryItems(f: ItemsFiltros): Record<string, string | undefined> {
  return { estado: f.estado }
}

function queryAsignaciones(f: AsignacionesInventarioFiltros): Record<string, string | undefined> {
  return { empleado_id: f.empleadoId }
}

function headersEmpresa(empresaIdOverride?: string): Record<string, string> | undefined {
  return empresaIdOverride ? { "X-Empresa-Id": empresaIdOverride } : undefined
}

function aQuery(params: Record<string, string | undefined>): string {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v) q.set(k, v)
  }
  return q.size ? `?${q}` : ""
}

/** Exporta las asignaciones de inventario con los MISMOS filtros que el listado. */
export function exportarInventarioAsignaciones(
  formato: FormatoExport,
  filtros: AsignacionesInventarioFiltros = {},
): Promise<void> {
  return descargarArchivo(
    `${ASIG}/exportar`, formato, "inventario_asignaciones",
    headersEmpresa(filtros.empresaIdOverride), queryAsignaciones(filtros),
  )
}

/** Exporta los ítems de inventario con los MISMOS filtros que el listado. */
export function exportarInventarioItems(
  formato: FormatoExport,
  filtros: ItemsFiltros = {},
): Promise<void> {
  return descargarArchivo(
    `${ITEMS}/exportar`, formato, "inventario_items",
    headersEmpresa(filtros.empresaIdOverride), queryItems(filtros),
  )
}

export async function fetchItems(filtros: ItemsFiltros = {}): Promise<ItemListResponse> {
  return apiFetch<ItemListResponse>(
    `${ITEMS}${aQuery(queryItems(filtros))}`, override(filtros.empresaIdOverride),
  )
}

export async function fetchItem(id: string): Promise<InventarioItem> {
  return apiFetch<InventarioItem>(`${ITEMS}/${id}`)
}

export async function createItem(data: InventarioItemCreate): Promise<InventarioItem> {
  return apiFetch<InventarioItem>(ITEMS, { method: "POST", body: JSON.stringify(data) })
}

export async function updateItem(id: string, data: InventarioItemUpdate): Promise<InventarioItem> {
  return apiFetch<InventarioItem>(`${ITEMS}/${id}`, { method: "PUT", body: JSON.stringify(data) })
}

export async function deleteItem(id: string): Promise<void> {
  await apiFetch<{ ok: boolean }>(`${ITEMS}/${id}`, { method: "DELETE" })
}

export async function fetchHistorialItem(id: string): Promise<AsignacionListResponse> {
  return apiFetch<AsignacionListResponse>(`${ITEMS}/${id}/historial`)
}

export async function fetchAsignaciones(
  filtros: AsignacionesInventarioFiltros = {},
): Promise<AsignacionListResponse> {
  return apiFetch<AsignacionListResponse>(
    `${ASIG}${aQuery(queryAsignaciones(filtros))}`, override(filtros.empresaIdOverride),
  )
}

export async function asignarItem(data: AsignacionCreate): Promise<Asignacion> {
  return apiFetch<Asignacion>(ASIG, { method: "POST", body: JSON.stringify(data) })
}

export async function devolverItem(id: string, data: DevolucionRequest): Promise<Asignacion> {
  return apiFetch<Asignacion>(`${ASIG}/${id}/devolver`, { method: "POST", body: JSON.stringify(data) })
}
