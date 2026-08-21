import type {
  CamposPerfilResponse, PerfilPuesto, PerfilPuestoCreate, PerfilPuestoListResponse,
  PerfilPuestoUpdate,
} from "@/types/perfilPuesto"
import { apiFetch, descargarArchivo, type FormatoExport } from "@/services/api"

/**
 * Los DOS filtros del catálogo, y no hay más. El backend acepta exactamente `search` (ilike sobre
 * el nombre) e `incluir_inactivos`; cualquier otro filtro que la pantalla ofreciera sería una
 * promesa que el listado no puede cumplir y que el export tampoco.
 *
 * ⚠️ NO HAY FILTRO DE EMPRESA, y no es que falte: **ninguna ruta de perfiles lee `X-Empresa-Id`**.
 * El catálogo es del GRUPO (migración 113), así que no viaja ni como query param ni como header.
 * Por eso estas funciones no pasan `headers` — a diferencia de casi todas sus hermanas.
 */
export interface PerfilesFiltros {
  search?: string
  incluirInactivos?: boolean
}

/**
 * Traducción filtros → query params. FUENTE ÚNICA: la consumen el listado y el export, que es lo
 * que hace estructuralmente imposible que un filtro quede en una sola de las dos puntas — y con
 * él, que el archivo traiga más filas de las que se ven en pantalla.
 */
function queryPerfiles(f: PerfilesFiltros): Record<string, string | undefined> {
  return {
    search: f.search || undefined,
    incluir_inactivos: f.incluirInactivos ? "true" : undefined,
  }
}

export async function fetchPerfiles(
  filtros: PerfilesFiltros = {}, page = 1, pageSize = 20,
): Promise<PerfilPuestoListResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
  for (const [k, v] of Object.entries(queryPerfiles(filtros))) {
    if (v) params.set(k, v)
  }
  return apiFetch<PerfilPuestoListResponse>(`/api/perfiles-puesto?${params}`)
}

/** Exporta el catálogo con los MISMOS filtros que la pantalla, sin paginar. */
export function exportarPerfiles(
  formato: FormatoExport, filtros: PerfilesFiltros = {},
): Promise<void> {
  return descargarArchivo("/api/perfiles-puesto/exportar", formato, "perfiles_puesto", undefined,
                          queryPerfiles(filtros))
}

/**
 * Labels, textos de ayuda y vocabularios del formulario.
 *
 * 🔴 EL FORMULARIO SE CONSTRUYE CON ESTO, no con una lista escrita en el front. Los tres
 * vocabularios cerrados son TAMBIÉN los `Literal` con los que valida el backend: una copia acá
 * que derive ofrecería en un select un valor que después sale rechazado con 422. Y los textos de
 * ayuda son lo único que impide que el bloque "Requisitos" del aviso se pegue entero en un solo
 * campo — ver `schemas/_perfil_puesto_campos.py`, que explica el modo de falla completo.
 */
export async function fetchCamposPerfil(): Promise<CamposPerfilResponse> {
  return apiFetch<CamposPerfilResponse>("/api/perfiles-puesto/campos")
}

/* ⚠️ NO hay `fetchPerfil(id)`, y su ausencia es deliberada: el listado devuelve el perfil ENTERO
 * —los 12 campos, no una proyección—, así que tanto el modal de edición como el de lectura
 * reciben el objeto que la pantalla ya tiene. Pedir la fila de vuelta sería una ida a la red por
 * nada. Es el mismo caso que clientes y que eventos, y el GET por id sigue publicado por
 * completitud REST, declarado con esa razón en `backend/tests/test_callers_huerfanos.py`.
 *
 * 🔴 Y por eso este comentario NO cita la ruta entre backticks: el escáner de paths de ese
 * barrido no distingue un comentario de un template literal, así que escribirla acá le "daría
 * caller" al endpoint y taparía el próximo caso. Es exactamente el hueco por el que `fetchCliente`
 * vivió cinco sesiones sin caller y el barrido en verde. */

export async function createPerfil(data: PerfilPuestoCreate): Promise<PerfilPuesto> {
  return apiFetch<PerfilPuesto>("/api/perfiles-puesto", {
    method: "POST", body: JSON.stringify(data),
  })
}

export async function updatePerfil(
  id: string, data: PerfilPuestoUpdate,
): Promise<PerfilPuesto> {
  return apiFetch<PerfilPuesto>(`/api/perfiles-puesto/${id}`, {
    method: "PUT", body: JSON.stringify(data),
  })
}

/**
 * Baja LÓGICA en el backend (`activo=False`), no borrado físico, y el 204 no dice cuál de las dos
 * fue. `vacantes.perfil_puesto_id` es una FK `ON DELETE SET NULL`: un borrado real no falla —y
 * por eso es peligroso— pero le arranca en silencio la trazabilidad a toda vacante creada desde
 * ese perfil. La baja lo saca de los selects, deja el vínculo intacto y es reversible desde la
 * pantalla (editar → Activo).
 */
export async function deletePerfil(id: string): Promise<void> {
  await apiFetch<void>(`/api/perfiles-puesto/${id}`, { method: "DELETE" })
}
