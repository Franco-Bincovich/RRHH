import type {
  Evento, EventoCreate, EventoListResponse, EventoUpdate,
} from "@/types/evento"
import { apiFetch } from "@/services/api"

/**
 * Filtros de la agenda. Un solo tipo, que viaja entero de la UI al service.
 *
 * ⚠️ El filtro de EMPRESA no viaja acá: el backend lo toma del header `X-Empresa-Id` (es una
 * VISTA, la manda el selector del sidebar).
 *
 * ⚠️ Y NO HAY EXPORT, así que este módulo es la única excepción del repo a "el mismo tipo lo
 * consumen el listado y el export": no hay segunda punta con la que divergir. Es decisión de
 * producto — una agenda de recordatorios no es un dato que se lleve a Excel; lo que se hace con
 * un evento es resolverlo.
 */
export interface EventosFiltros {
  incluirResueltas?: boolean
}

/** Traducción filtros → query params. Fuente única del listado. */
function queryEventos(f: EventosFiltros): Record<string, string | undefined> {
  return { incluir_resueltas: f.incluirResueltas ? "true" : undefined }
}

export async function fetchEventos(
  filtros: EventosFiltros = {}, page = 1, pageSize = 20,
): Promise<EventoListResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  for (const [k, v] of Object.entries(queryEventos(filtros))) {
    if (v) params.set(k, v)
  }
  return apiFetch<EventoListResponse>(`/api/eventos?${params}`)
}

/* ⚠️ NO hay `fetchEvento(id)`, y su ausencia es deliberada: el modal de edición recibe el objeto
 * ENTERO del listado, así que pedir la fila de vuelta sería una ida a la red para traer lo que la
 * pantalla ya tiene. El GET por id sigue publicado por completitud REST.
 *
 * ⚠️ Y este comentario NO cita la ruta entre backticks: el escáner de paths del barrido de
 * endpoints huérfanos no distingue un comentario de un template literal, así que escribirla acá
 * le "daría caller" al endpoint y taparía el próximo caso. Es el hueco documentado en
 * services/clientes.ts.
 *
 * ⚠️ Tampoco está todavía el wrapper de los PENDIENTES (los que entraron en su ventana de aviso).
 * Ese endpoint existe en el backend desde esta misma sesión y lo va a consumir la tarjeta del
 * dashboard, que es la sesión 2; está declarado como huérfano CON su disparador en
 * backend/tests/test_callers_huerfanos.py. */

export async function createEvento(data: EventoCreate): Promise<Evento> {
  return apiFetch<Evento>("/api/eventos", { method: "POST", body: JSON.stringify(data) })
}

export async function updateEvento(id: string, data: EventoUpdate): Promise<Evento> {
  return apiFetch<Evento>(`/api/eventos/${id}`, { method: "PUT", body: JSON.stringify(data) })
}

/**
 * Marca o desmarca como resuelto. UN endpoint para los dos sentidos: resolver es reversible, y
 * el front manda el estado que QUIERE en vez de un incremento sobre uno que puede estar viejo.
 */
export async function setEventoResuelta(id: string, resuelta: boolean): Promise<Evento> {
  return apiFetch<Evento>(`/api/eventos/${id}/resuelta`, {
    method: "PUT", body: JSON.stringify({ resuelta }),
  })
}

/** Baja FÍSICA, al revés que clientes: un evento borrado no sobrevive en ningún listado. Su
 *  snapshot queda en la auditoría. Ver backend/services/_eventos_write.py. */
export async function deleteEvento(id: string): Promise<void> {
  await apiFetch<void>(`/api/eventos/${id}`, { method: "DELETE" })
}
