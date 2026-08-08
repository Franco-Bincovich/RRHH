import type {
  VacacionPendiente,
  VacacionPendienteCreate,
  VacacionPendienteListResponse,
} from "@/types/vacaciones"
import { apiFetch, descargarArchivo, type FormatoExport } from "@/services/api"

/**
 * Días de vacaciones NO tomados. Endpoint propio (/api/vacaciones-pendientes) y no anidado
 * bajo /api/vacaciones, porque el GET /api/vacaciones/{id} del backend se comería la ruta.
 *
 * Sin filtros propios a propósito: la pantalla los muestra bajo el mismo selector de empresa
 * del sidebar, y sumar una barra de filtros aparte daría dos superficies de filtrado sobre
 * el mismo módulo. El endpoint ya acepta area_id/empleado_id/proyecto_id para cuando se defina.
 */
export async function fetchVacacionesPendientes(
  page = 1,
  pageSize = 20,
): Promise<VacacionPendienteListResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  return apiFetch<VacacionPendienteListResponse>(`/api/vacaciones-pendientes?${params}`)
}

/**
 * Exporta los días pendientes — los MISMOS que muestra la pantalla.
 *
 * No manda query params, igual que `fetchVacacionesPendientes` (que solo pasa page/page_size,
 * y el export no se pagina por diseño). 🔴 El día que la pantalla gane la barra de filtros que
 * el endpoint ya acepta (area_id / empleado_id / proyecto_id), los dos tienen que armar sus
 * params con UNA función de traducción compartida — molde: `queryVacaciones` en vacaciones.ts.
 *
 * El recorte que de verdad importa acá no viaja por la URL: el backend acota por OWNERSHIP a
 * partir del token, así que un mando medio recibe solo a su gente.
 */
export function exportarVacacionesPendientes(formato: FormatoExport): Promise<void> {
  return descargarArchivo("/api/vacaciones-pendientes/exportar", formato, "vacaciones_pendientes")
}

export async function createVacacionPendiente(
  data: VacacionPendienteCreate,
): Promise<VacacionPendiente> {
  return apiFetch<VacacionPendiente>("/api/vacaciones-pendientes", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

/** Edita el registro. Hoy la UI solo cambia `dias_liquidados` (el tilde "Liquidada"). */
export async function updateVacacionPendiente(
  id: string,
  data: Partial<VacacionPendienteCreate>,
): Promise<VacacionPendiente> {
  return apiFetch<VacacionPendiente>(`/api/vacaciones-pendientes/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  })
}

export async function deleteVacacionPendiente(id: string): Promise<void> {
  await apiFetch<void>(`/api/vacaciones-pendientes/${id}`, { method: "DELETE" })
}
