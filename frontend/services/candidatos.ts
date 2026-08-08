import { apiFetch, API_BASE, ApiError, authHeaders, descargarArchivo, type FormatoExport } from "@/services/api"
import type { CandidatoConGrupo } from "@/types/candidato"

/** Lista todos los candidatos de la empresa activa (con y sin vacante), con su grupo resuelto. */
export function getCandidatos(): Promise<CandidatoConGrupo[]> {
  return apiFetch<CandidatoConGrupo[]>("/api/candidatos")
}

/**
 * Exporta los candidatos. El listado no tiene filtros propios —la empresa viaja por el header
 * `X-Empresa-Id` que pone `apiFetch`, igual que en `getCandidatos`—, así que las dos puntas
 * traen el mismo conjunto por construcción: no hay query params que puedan divergir.
 */
export function exportarCandidatos(formato: FormatoExport): Promise<void> {
  return descargarArchivo("/api/candidatos/exportar", formato, "candidatos")
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
