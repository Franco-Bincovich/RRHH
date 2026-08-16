// Servicio de reportes de resultados de evaluaciones (lectura + export). El lote sale del
// selector de ciclo; la empresa la resuelve el header (el lote ya la fija en el backend).
import { apiFetch, API_BASE, ApiError, authHeaders, descargarArchivo } from "@/services/api"
import type {
  EvaluadoListadoResponse, FichaResponse, LotesBulkResult, LotesResponse, MetricasResponse,
} from "@/types/evaluacionReportes"

const BASE = "/api/evaluaciones/resultados"

export interface FiltrosEvaluados {
  sector?: string
  perfil?: string
  con_nota?: string
  proyecto_id?: string
}

/**
 * Traducción filtros → query params. FUENTE ÚNICA del listado y del export.
 *
 * 🔴 LOS CUATRO SON SERVER-SIDE DESDE EL 15/8/2026. Hasta entonces sólo `proyecto_id` viajaba
 * y los otros tres se aplicaban sobre el array ya traído: con ~30 filas por lote se veía bien,
 * pero paginar convierte eso en "filtrar por sector no encuentra a nadie que no esté en la
 * página que estás mirando". Ahora los cuatro van al WHERE, y el export usa este mismo
 * traductor — que es lo que hace imposible que un filtro quede en una sola de las dos puntas.
 */
function queryEvaluados(f: FiltrosEvaluados): Record<string, string | undefined> {
  return { sector: f.sector, perfil: f.perfil, con_nota: f.con_nota, proyecto_id: f.proyecto_id }
}

export async function fetchLotesEvaluaciones(): Promise<LotesResponse> {
  return apiFetch<LotesResponse>(`${BASE}/lotes`)
}

/**
 * Historial: TODOS los lotes de TODAS las empresas. Fuerza X-Empresa-Id "todas" (consolidado)
 * para no depender del selector del sidebar — el backend ya desacopló el listado y el borrado.
 */
export async function fetchLotesHistorial(): Promise<LotesResponse> {
  return apiFetch<LotesResponse>(`${BASE}/lotes`, { headers: { "X-Empresa-Id": "todas" } })
}

/** Baja múltiple: devuelve la clasificación { eliminados, fallidos } (no aborta si uno falla). */
export async function deleteLotesBulk(loteIds: string[]): Promise<LotesBulkResult> {
  return apiFetch<LotesBulkResult>(`${BASE}/lotes/eliminar`, {
    method: "POST",
    body: JSON.stringify({ lote_ids: loteIds }),
  })
}

/**
 * Elimina la importación completa: el CASCADE se lleva evaluados y resultados. Las
 * equivalencias de nombres sobreviven (cuelgan de la empresa, no del lote).
 * fetch crudo en vez de apiFetch: el endpoint responde 204 sin body.
 */
export async function deleteLoteEvaluacion(loteId: string): Promise<void> {
  const res = await fetch(`${API_BASE}${BASE}/lotes/${loteId}`, {
    method: "DELETE",
    headers: authHeaders(),
  })
  if (!res.ok) {
    let msg = "No se pudo eliminar la importación."
    try { msg = ((await res.json()) as { message?: string }).message ?? msg } catch { /* sin body */ }
    throw new ApiError(msg, "UNKNOWN", res.status)
  }
}

export async function fetchMetricas(loteId: string): Promise<MetricasResponse> {
  return apiFetch<MetricasResponse>(`${BASE}/lotes/${loteId}/metricas`)
}

/**
 * Una página de evaluados del lote. `page`/`page_size` quedan FUERA de `queryEvaluados` a
 * propósito: son lo único que el listado tiene y el export no (el export no se pagina).
 */
export async function fetchEvaluadosResultados(
  loteId: string, filtros: FiltrosEvaluados = {}, page = 1, pageSize = 20,
): Promise<EvaluadoListadoResponse> {
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(queryEvaluados(filtros))) if (v) params.set(k, v)
  params.set("page", String(page))
  params.set("page_size", String(pageSize))
  return apiFetch<EvaluadoListadoResponse>(`${BASE}/lotes/${loteId}/evaluados?${params}`)
}

export async function fetchFicha(loteId: string, evaluadoId: string): Promise<FichaResponse> {
  return apiFetch<FichaResponse>(`${BASE}/lotes/${loteId}/evaluados/${evaluadoId}/ficha`)
}

export function exportarEvaluadosResultados(
  loteId: string, formato: string, f: FiltrosEvaluados,
): Promise<void> {
  // Mismos Query que el listado (estándar 1.2), por el MISMO traductor: enumerarlos otra vez
  // acá era la forma de que un filtro nuevo entrara al listado y no al archivo.
  return descargarArchivo(
    `${BASE}/lotes/${loteId}/evaluados/export`, formato, "evaluaciones_resultados", undefined,
    queryEvaluados(f),
  )
}
