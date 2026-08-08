import type { Area, AreaCreate, AreaUpdate } from "@/types/area"
import { apiFetch, descargarArchivo, type FormatoExport } from "@/services/api"

/**
 * Traducción filtros → query params del módulo de áreas. Fuente ÚNICA: la consumen el listado y
 * el export, que es lo que hace estructuralmente imposible que el filtro quede en una sola de las
 * dos puntas. Hoy el módulo filtra por un solo campo; el molde vale igual para el segundo.
 */
function queryAreas(empresaId?: string): Record<string, string | undefined> {
  return { empresa_id: empresaId }
}

export async function fetchAreas(empresaId?: string): Promise<Area[]> {
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(queryAreas(empresaId))) {
    if (v) params.set(k, v)
  }
  return apiFetch<Area[]>(params.size ? `/api/areas?${params}` : "/api/areas")
}

/** Exporta el listado de áreas con el MISMO filtro que la pantalla. */
export function exportarAreas(formato: FormatoExport, empresaId?: string): Promise<void> {
  return descargarArchivo("/api/areas/exportar", formato, "areas", undefined, queryAreas(empresaId))
}

export async function fetchArea(id: string): Promise<Area> {
  return apiFetch<Area>(`/api/areas/${id}`)
}

export async function createArea(data: AreaCreate): Promise<Area> {
  return apiFetch<Area>("/api/areas", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function updateArea(id: string, data: AreaUpdate): Promise<Area> {
  return apiFetch<Area>(`/api/areas/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  })
}

export async function deleteArea(id: string): Promise<void> {
  await apiFetch<void>(`/api/areas/${id}`, { method: "DELETE" })
}
