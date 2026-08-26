import type {
  VacacionPendiente,
  VacacionPendienteCreate,
  VacacionPendienteListResponse,
} from "@/types/vacaciones"
import type { VacacionesFiltros } from "@/services/vacaciones"
import { apiFetch, descargarArchivo, type FormatoExport } from "@/services/api"

/**
 * Días de vacaciones NO tomados. Endpoint propio (/api/vacaciones-pendientes) y no anidado
 * bajo /api/vacaciones, porque el GET /api/vacaciones/{id} del backend se comería la ruta.
 *
 * 🔴 LOS FILTROS SON LOS DE LA PANTALLA, NO UNOS PROPIOS (bloque N8, 25/8/2026). El endpoint
 * acepta `area_id`, `empleado_id` y `proyecto_id` desde que existe, y el front no le mandaba
 * ninguno: la tabla de días pendientes ignoraba la barra de filtros que estaba justo arriba de
 * ella, así que filtrar por un área dejaba el listado de arriba recortado y **el de abajo entero**
 * — dos números sobre la misma pantalla que no se pueden conciliar, y el export bajaba el padrón
 * completo.
 *
 * El comentario que estaba acá decía que no tenía filtros "a propósito, para no dar dos
 * superficies de filtrado sobre el mismo módulo". Ese razonamiento se respeta y por eso NO se le
 * agregó una barra propia: **reusa la de /vacaciones**, que ya ofrece los tres. Sigue habiendo una
 * sola superficie; lo que cambió es que ahora gobierna las dos tablas.
 *
 * ⚠️ Toma `VacacionesFiltros` entero y descarta lo que este endpoint no acepta (`estado` y el
 * rango de fechas, que no aplican a un saldo). Recibir el mismo tipo que la pantalla ya tiene es
 * lo que hace imposible el corrimiento de argumentos; filtrar acá lo que no viaja es una línea.
 */
function queryPendientes(f: VacacionesFiltros): Record<string, string | undefined> {
  return { area_id: f.areaId, empleado_id: f.empleadoId, proyecto_id: f.proyectoId }
}

export async function fetchVacacionesPendientes(
  page = 1,
  pageSize = 20,
  filtros: VacacionesFiltros = {},
): Promise<VacacionPendienteListResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  for (const [k, v] of Object.entries(queryPendientes(filtros))) {
    if (v) params.set(k, v)
  }
  return apiFetch<VacacionPendienteListResponse>(`/api/vacaciones-pendientes?${params}`)
}

/**
 * Exporta los días pendientes — los MISMOS que muestra la pantalla.
 *
 * 🔴 USA `queryPendientes`, LA MISMA TRADUCCIÓN QUE EL LISTADO. Es la invariante 2 del bloque B y
 * acá no era teórica: hasta hoy los dos mandaban CERO filtros, así que el archivo y la pantalla
 * coincidían por casualidad. En el momento en que el listado empezara a filtrar y el export no,
 * el Excel saldría con más filas de las que se ven — sin error y sin aviso.
 *
 * El recorte que de verdad importa acá no viaja por la URL: el backend acota por OWNERSHIP a
 * partir del token, así que un mando medio recibe solo a su gente.
 */
export function exportarVacacionesPendientes(
  formato: FormatoExport,
  filtros: VacacionesFiltros = {},
): Promise<void> {
  return descargarArchivo("/api/vacaciones-pendientes/exportar", formato, "vacaciones_pendientes",
    undefined, queryPendientes(filtros))
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
