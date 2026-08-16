import type { Area, AreaCreate, AreaListResponse, AreaUpdate } from "@/types/area"
import { apiFetch, descargarArchivo, type FormatoExport } from "@/services/api"

/**
 * Traducción filtros → query params del módulo de áreas. Fuente ÚNICA: la consumen el listado y
 * el export, que es lo que hace estructuralmente imposible que el filtro quede en una sola de las
 * dos puntas. Hoy el módulo filtra por un solo campo; el molde vale igual para el segundo.
 */
function queryAreas(empresaId?: string, search?: string): Record<string, string | undefined> {
  return { empresa_id: empresaId, search: search || undefined }
}

/**
 * EL CATÁLOGO COMPLETO de áreas, para poblar selects. Pega a `/api/areas/opciones`.
 *
 * 🔴 NO PAGINA, Y POR ESO NO PEGA AL LISTADO. La usan ~15 selectores y filtros de área en todo
 * el front (vacaciones, ausencias, inventario, capacitaciones, proyectos, reportes, sucesión,
 * los modales de empleado y vacante…). Cuando `/api/areas` pasó a paginar, apuntar esta función
 * ahí habría dejado cada dropdown mostrando 20 de ~180 — sin error, sólo áreas que "no existen".
 * Mover la función a otra ruta dejó los 14 archivos consumidores sin tocar.
 *
 * La pantalla de gestión de áreas usa `fetchAreasPagina`.
 */
export async function fetchAreas(empresaId?: string): Promise<Area[]> {
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(queryAreas(empresaId))) {
    if (v) params.set(k, v)
  }
  return apiFetch<Area[]>(params.size ? `/api/areas/opciones?${params}` : "/api/areas/opciones")
}

/** Una página del listado de gestión, con búsqueda por nombre resuelta en el servidor. */
export async function fetchAreasPagina(
  empresaId?: string, search?: string, page = 1, pageSize = 20,
): Promise<AreaListResponse> {
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(queryAreas(empresaId, search))) {
    if (v) params.set(k, v)
  }
  // Aparte de `queryAreas`, que comparte con el export: el export no se pagina.
  params.set("page", String(page))
  params.set("page_size", String(pageSize))
  return apiFetch<AreaListResponse>(`/api/areas?${params}`)
}

/** Exporta el listado con los MISMOS filtros que la pantalla, `search` incluido. */
export function exportarAreas(formato: FormatoExport, empresaId?: string, search?: string): Promise<void> {
  return descargarArchivo("/api/areas/exportar", formato, "areas", undefined, queryAreas(empresaId, search))
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
