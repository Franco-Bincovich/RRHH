import { apiFetch, API_BASE, ApiError, authHeaders, descargarArchivo, type FormatoExport } from "@/services/api"
import type { CandidatoConGrupo, CandidatosPagina, FiltroClasificacion } from "@/types/candidato"
import type { Empleado } from "@/types/empleado"

export interface CandidatosFiltros {
  /** Solo los huérfanos: los que entraron sin matchear ninguna búsqueda. */
  sinVacante?: boolean
  /** Corte por resultado del screening. `undefined` = todos, sin filtrar. */
  clasificacion?: FiltroClasificacion
}

/**
 * Traducción filtros → query params. FUENTE ÚNICA del listado y del export.
 *
 * 🔴 Que los dos pasen por acá es lo que hace estructuralmente imposible que un filtro quede en
 * una sola de las dos puntas. El bug clásico es sumar un filtro al listado y que el archivo salga
 * con MÁS filas de las que se ven, sin error y sin aviso. Molde: `queryVacantes`.
 */
function queryCandidatos(f: CandidatosFiltros): Record<string, string | undefined> {
  return { sin_vacante: f.sinVacante ? "true" : undefined, clasificacion: f.clasificacion }
}

/**
 * Una página de candidatos de la empresa activa, con su grupo resuelto.
 *
 * 🔴 `page`/`pageSize` NO entran en `queryCandidatos`, y no es un olvido: son lo ÚNICO que el
 * listado tiene y el export no. El export no se pagina (invariante del Bloque B), así que si
 * el traductor compartido los emitiera, el archivo saldría con las primeras 20 filas.
 */
export function getCandidatos(
  filtros: CandidatosFiltros = {}, page = 1, pageSize = 20,
): Promise<CandidatosPagina> {
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(queryCandidatos(filtros))) if (v) params.set(k, v)
  params.set("page", String(page))
  params.set("page_size", String(pageSize))
  return apiFetch<CandidatosPagina>(`/api/candidatos?${params}`)
}

/** Exporta con los MISMOS filtros que muestra la pantalla, por el mismo traductor. */
export function exportarCandidatos(formato: FormatoExport, filtros: CandidatosFiltros = {}): Promise<void> {
  return descargarArchivo("/api/candidatos/exportar", formato, "candidatos", undefined,
                          queryCandidatos(filtros))
}

/** Asigna una vacante a un candidato huérfano. La vacante tiene que ser de SU empresa. */
export function asignarVacanteACandidato(id: string, vacanteId: string): Promise<CandidatoConGrupo> {
  return apiFetch<CandidatoConGrupo>(`/api/candidatos/${id}/vacante`, {
    method: "PUT", body: JSON.stringify({ vacante_id: vacanteId }),
  })
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

/**
 * Contrata a un candidato en oferta: crea su legajo de empleado en estado `preingreso`.
 *
 * 🔴 SOLO TRES CAMPOS, y no es un formulario recortado: es el punto del puente. Todo lo demás
 * (nombre, apellido, email personal, empresa, área) el backend lo deriva del candidato y de su
 * vacante. Los tres que van no existen en ninguna de las dos tablas y no se pueden inventar:
 *   · `email_corporativo` — NO es `candidato.email`, que es personal. La columna es UNIQUE
 *     GLOBAL, así que meterle el mail personal de alguien lo quema para todo el sistema.
 *   · `roles` — `vacante.titulo` es el texto del aviso, no el rol del legajo.
 *   · `fecha_ingreso` — es el acuerdo al que se llegó.
 * Agregar un cuarto campo es convertir el puente en un alta de empleado con pasos extra.
 *
 * 🔴 LA FECHA VA HACIA ADELANTE (`>= hoy`), al revés que `activarEmpleado`, que exige que ya
 * haya ocurrido. No es una inconsistencia: contratar registra un acuerdo futuro y crea la ficha
 * en `preingreso`; activar la pasa a `activo` el día que la persona entró. Si ya entró, el
 * camino es el alta normal de empleado.
 *
 * Los seis errores se muestran con su mensaje: CANDIDATO_NOT_FOUND (404), CANDIDATO_SIN_VACANTE,
 * CANDIDATO_NO_ESTA_EN_OFERTA, CANDIDATO_NO_CONTRATABLE (409), FECHA_INGRESO_PASADA (400), y el
 * 409 de `email_corporativo` ya usado que llega desde el alta de empleado.
 */
export function contratarCandidato(
  id: string,
  datos: { email_corporativo: string; roles: string[]; fecha_ingreso: string },
): Promise<Empleado> {
  return apiFetch<Empleado>(`/api/candidatos/${id}/contratar`, {
    method: "POST", body: JSON.stringify(datos),
  })
}
