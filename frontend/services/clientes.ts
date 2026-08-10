import type {
  Cliente, ClienteCreate, ClienteListResponse, ClienteUpdate,
} from "@/types/cliente"
import { apiFetch, descargarArchivo, type FormatoExport } from "@/services/api"

/** Filtros del catálogo de clientes. Un solo tipo, que viaja entero de la UI al service. */
export interface ClientesFiltros {
  incluirInactivos?: boolean
}

/**
 * Traducción filtros → query params. FUENTE ÚNICA: la consumen el listado y el export, que es
 * lo que hace estructuralmente imposible que un filtro quede en una sola de las dos puntas —
 * y con él, que el archivo traiga más filas de las que se ven en pantalla.
 *
 * ⚠️ El filtro de EMPRESA no viaja acá: el backend lo toma del header `X-Empresa-Id` (es una
 * VISTA, la manda el selector del sidebar). Por eso el export tampoco lo lleva como param.
 */
function queryClientes(f: ClientesFiltros): Record<string, string | undefined> {
  return { incluir_inactivos: f.incluirInactivos ? "true" : undefined }
}

export async function fetchClientes(filtros: ClientesFiltros = {}): Promise<ClienteListResponse> {
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(queryClientes(filtros))) {
    if (v) params.set(k, v)
  }
  return apiFetch<ClienteListResponse>(
    params.size ? `/api/clientes?${params}` : "/api/clientes")
}

/** Exporta el catálogo con los MISMOS filtros que la pantalla. */
export function exportarClientes(
  formato: FormatoExport, filtros: ClientesFiltros = {},
): Promise<void> {
  return descargarArchivo("/api/clientes/exportar", formato, "clientes", undefined,
                          queryClientes(filtros))
}

/* ⚠️ NO hay `fetchCliente(id)`, y su ausencia es deliberada: el modal de edición recibe el
 * objeto ENTERO del listado, así que pedir la fila de vuelta sería una ida a la red para
 * traer lo que la pantalla ya tiene. El GET por id sigue publicado por completitud REST y
 * está declarado en `backend/tests/test_callers_huerfanos.py` con esa razón.
 *
 * 🔴 Se borró el 2026-08-10 después de nacer sin un solo caller, y el barrido de endpoints NO
 * podía verlo: empareja (path, método) contra los LITERALES que aparecen en el front, y el
 * mismo path por id lo escriben también `updateCliente` y `deleteCliente`. El GET quedó tapado
 * por sus hermanos. Lo que sí lo habría visto es `barridoFront.test.ts` — leer su encabezado.
 *
 * ⚠️ Y por eso este comentario NO cita la ruta entre backticks: el escáner de paths no
 * distingue un comentario de un template literal, así que escribirla acá volvería a
 * "dar caller" al endpoint y a tapar el próximo caso. Es el mismo hueco, un renglón más
 * arriba. */

export async function createCliente(data: ClienteCreate): Promise<Cliente> {
  return apiFetch<Cliente>("/api/clientes", { method: "POST", body: JSON.stringify(data) })
}

export async function updateCliente(id: string, data: ClienteUpdate): Promise<Cliente> {
  return apiFetch<Cliente>(`/api/clientes/${id}`, { method: "PUT", body: JSON.stringify(data) })
}

/** Baja LÓGICA en el backend (`activo=False`): el cliente sale de los selects y las horas ya
 *  cargadas contra él quedan intactas. Ver services/cliente_service.py. */
export async function deleteCliente(id: string): Promise<void> {
  await apiFetch<void>(`/api/clientes/${id}`, { method: "DELETE" })
}
