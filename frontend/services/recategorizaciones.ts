import type {
  Recategorizacion, RecategorizacionCreate, RecategorizacionListResponse, RecategorizacionUpdate,
} from "@/types/recategorizacion"
import { apiFetch, descargarArchivo, type FormatoExport } from "@/services/api"

/**
 * Los TRES filtros de la planilla, y no hay más. El backend acepta exactamente `empleado_id`,
 * `fecha_desde` y `fecha_hasta`.
 *
 * ⚠️ NO HAY FILTRO DE ÁREA NI DE EMPRESA. La empresa viaja por el header `X-Empresa-Id` (es una
 * VISTA, la manda el selector del sidebar) y por área el backend directamente no filtra. Ofrecer
 * un filtro por área acá lo dejaría filtrando en el cliente sobre la página que llegó, mientras
 * el export —que va server-side— seguiría trayendo todo: el archivo saldría con más filas de las
 * que se ven. Es la invariante 1 del bloque B.
 *
 * ⚠️ El rango filtra por `fecha_efectiva` —cuándo RIGIÓ— y no por `created_at` —cuándo se cargó—.
 * Con una carga retroactiva las dos difieren, y la pregunta de RRHH es siempre la primera.
 */
export interface RecategorizacionesFiltros {
  empleadoId?: string
  fechaDesde?: string
  fechaHasta?: string
}

/**
 * Traducción filtros → query params. FUENTE ÚNICA: la consumen el listado y el export, que es lo
 * que hace estructuralmente imposible que un filtro quede en una sola de las dos puntas.
 */
function queryRecategorizaciones(
  f: RecategorizacionesFiltros,
): Record<string, string | undefined> {
  return {
    empleado_id: f.empleadoId || undefined,
    fecha_desde: f.fechaDesde || undefined,
    fecha_hasta: f.fechaHasta || undefined,
  }
}

export async function fetchRecategorizaciones(
  filtros: RecategorizacionesFiltros = {}, page = 1, pageSize = 20,
): Promise<RecategorizacionListResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  for (const [k, v] of Object.entries(queryRecategorizaciones(filtros))) {
    if (v) params.set(k, v)
  }
  return apiFetch<RecategorizacionListResponse>(`/api/recategorizaciones?${params}`)
}

/** Exporta la planilla con los MISMOS filtros que la pantalla, sin paginar. */
export function exportarRecategorizaciones(
  formato: FormatoExport, filtros: RecategorizacionesFiltros = {},
): Promise<void> {
  return descargarArchivo("/api/recategorizaciones/exportar", formato, "recategorizaciones",
                          undefined, queryRecategorizaciones(filtros))
}

/**
 * El historial de UNA persona: lista plana, del más reciente al más viejo, SIN paginar.
 *
 * Es la segunda vista de la misma tabla y tiene forma distinta a propósito: son una o dos por
 * persona por año, así que paginar sería un paginador de una sola página. Molde exacto:
 * `fetchHistorialSalarial`, que alimenta el otro historial de esa misma ficha.
 *
 * 🔴 TIENE DOS CONSUMIDORES Y EL SEGUNDO NO ES OBVIO: el panel de la ficha, y el MODAL de alta —
 * que lo necesita para saber cuál es la última recategorización de esa persona y avisar, en el
 * momento, si la fecha elegida es retroactiva. Ver `avisoRetroactivo`.
 */
export async function fetchHistorialRecategorizaciones(
  empleadoId: string,
): Promise<Recategorizacion[]> {
  return apiFetch<Recategorizacion[]>(`/api/empleados/${empleadoId}/recategorizaciones`)
}

export async function createRecategorizacion(
  data: RecategorizacionCreate,
): Promise<Recategorizacion> {
  return apiFetch<Recategorizacion>("/api/recategorizaciones", {
    method: "POST", body: JSON.stringify(data),
  })
}

export async function updateRecategorizacion(
  id: string, data: RecategorizacionUpdate,
): Promise<Recategorizacion> {
  return apiFetch<Recategorizacion>(`/api/recategorizaciones/${id}`, {
    method: "PUT", body: JSON.stringify(data),
  })
}

/* 🔴 NO HAY `deleteRecategorizacion`, Y NO PORQUE FALTE ESCRIBIRLO: el backend NO PUBLICA un
 * DELETE. Borrar una fila rompe la cadena de valores anteriores que cuelga de ella —la siguiente
 * quedaría afirmando un valor previo que ya no existe en ningún lado— y la auditoría ya registra
 * quién editó qué. La corrección es editar, no borrar. Ninguna superficie de la pantalla ofrece
 * esa acción, y hay un test que lo verifica en las tres (planilla, modal y ficha).
 *
 * ⚠️ Tampoco hay un `fetchRecategorizacion(id)`: el listado devuelve la fila ENTERA, así que el
 * modal de edición recibe el objeto que la pantalla ya tiene. El GET por id sigue publicado por
 * completitud REST y está declarado con esa razón en el barrido de endpoints del backend. Este
 * comentario NO cita las rutas entre backticks a propósito — el escáner de ese barrido no
 * distingue un comentario de un template literal, y escribirlas acá le "daría caller" al
 * endpoint y taparía el próximo caso. */
