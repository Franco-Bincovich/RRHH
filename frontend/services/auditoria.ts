import { apiFetch, descargarArchivo, type FormatoExport } from "@/services/api"
import type { AuditLogListResponse } from "@/types/auditoria"

const BASE = "/api/auditoria"

/**
 * Filtros del listado de auditoría. Los consumen el listado Y el export: es el mismo tipo a
 * propósito, para que un filtro nuevo no pueda quedar en uno solo de los dos
 * (invariante list ↔ export).
 */
export interface AuditoriaFiltros {
  usuario_id?: string
  entidad?: string
  evento?: string
  registro_id?: string
  fecha_desde?: string
  fecha_hasta?: string
  page?: number
  page_size?: number
}

/**
 * Traducción filtros → query params. Fuente ÚNICA compartida por listado y export: si se suma
 * un filtro, se suma acá una sola vez y le llega a los dos.
 *
 * `page`/`page_size` quedan afuera a propósito: el export NO se pagina (invariante del repo),
 * así que los agrega solo el listado.
 */
function queryAuditoria(f: AuditoriaFiltros): Record<string, string | undefined> {
  return {
    usuario_id: f.usuario_id,
    entidad: f.entidad,
    evento: f.evento,
    registro_id: f.registro_id,
    fecha_desde: f.fecha_desde,
    fecha_hasta: f.fecha_hasta,
  }
}

function aQuery(params: Record<string, string | undefined>): string {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v) q.set(k, v)
  }
  return q.size ? `?${q}` : ""
}

/**
 * Lista eventos de auditoría paginados y filtrados.
 * empresa_id NO va como query param: apiFetch ya inyecta X-Empresa-Id del empresaStore
 * (consolidado o empresa activa), igual que todos los listados.
 */
export async function fetchAuditoria(filtros: AuditoriaFiltros = {}): Promise<AuditLogListResponse> {
  const params = queryAuditoria(filtros)
  if (filtros.page) params.page = String(filtros.page)
  if (filtros.page_size) params.page_size = String(filtros.page_size)
  return apiFetch<AuditLogListResponse>(`${BASE}${aQuery(params)}`)
}

/** Exporta el listado de auditoría con los MISMOS filtros que el listado. */
export function exportarAuditoria(
  formato: FormatoExport,
  filtros: AuditoriaFiltros = {},
): Promise<void> {
  return descargarArchivo(`${BASE}/exportar`, formato, "auditoria", undefined, queryAuditoria(filtros))
}
