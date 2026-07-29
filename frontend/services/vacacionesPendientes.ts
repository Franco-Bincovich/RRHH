import type {
  VacacionPendiente,
  VacacionPendienteCreate,
  VacacionPendienteListResponse,
} from "@/types/vacaciones"
import { apiFetch } from "@/services/api"

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
