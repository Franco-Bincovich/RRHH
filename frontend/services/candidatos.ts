import { apiFetch, API_BASE, ApiError, authHeaders, descargarArchivo, type FormatoExport } from "@/services/api"
import type { CandidatoConGrupo, FiltroClasificacion } from "@/types/candidato"

export interface CandidatosFiltros {
  /** Solo los huérfanos: los que entraron sin matchear ninguna búsqueda. */
  sinVacante?: boolean
  /** Corte por resultado del screening. `undefined` = todos, sin filtrar. */
  clasificacion?: FiltroClasificacion
}

/**
 * Traducción filtros → query params. FUENTE ÚNICA del listado y del export.
 *
 * 🔴 Que los dos pasen por acá es lo que hace estructuralmente imposible que un filtro quede en
 * una sola de las dos puntas. El bug clásico es sumar un filtro al listado y que el archivo salga
 * con MÁS filas de las que se ven, sin error y sin aviso. Molde: `queryVacantes`.
 */
function queryCandidatos(f: CandidatosFiltros): Record<string, string | undefined> {
  return { sin_vacante: f.sinVacante ? "true" : undefined, clasificacion: f.clasificacion }
}

/** Lista los candidatos de la empresa activa, con su grupo resuelto. */
export function getCandidatos(filtros: CandidatosFiltros = {}): Promise<CandidatoConGrupo[]> {
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(queryCandidatos(filtros))) if (v) params.set(k, v)
  const query = params.toString() ? `?${params}` : ""
  return apiFetch<CandidatoConGrupo[]>(`/api/candidatos${query}`)
}

/** Exporta con los MISMOS filtros que muestra la pantalla, por el mismo traductor. */
export function exportarCandidatos(formato: FormatoExport, filtros: CandidatosFiltros = {}): Promise<void> {
  return descargarArchivo("/api/candidatos/exportar", formato, "candidatos", undefined,
                          queryCandidatos(filtros))
}

/** Asigna una vacante a un candidato huérfano. La vacante tiene que ser de SU empresa. */
export function asignarVacanteACandidato(id: string, vacanteId: string): Promise<CandidatoConGrupo> {
  return apiFetch<CandidatoConGrupo>(`/api/candidatos/${id}/vacante`, {
    method: "PUT", body: JSON.stringify({ vacante_id: vacanteId }),
  })
}

/** Devuelve una signed URL temporal para abrir el CV del candidato (bucket privado). */
export async function getCandidatoCvUrl(id: string): Promise<string> {
  const data = await apiFetch<{ url: string }>(`/api/candidatos/${id}/cv-url`)
  return data.url
}

/** Elimina un candidato huérfano (y su CV del Storage). El endpoint devuelve 204 → no parsea JSON. */
export async function deleteCandidato(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/candidatos/${id}`, { method: "DELETE", headers: authHeaders() })
  if (!res.ok) {
    let msg = "No se pudo eliminar el candidato."
    try { msg = ((await res.json()) as { message?: string }).message ?? msg } catch { /* sin body */ }
    throw new ApiError(msg, "UNKNOWN", res.status)
  }
}
