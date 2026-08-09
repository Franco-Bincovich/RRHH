import type { AsignacionResultado, AvisoPostulacion, Candidato, CandidatoCreate, EtapaPipeline, IngestaResultado, LinkedinPublicarRequest, LinkedinPublicarResponse, MailPendiente, Vacante, VacanteCreate, VacanteUpdate } from "@/types/vacantes"
import {
  apiFetch, API_BASE, ApiError, authHeaders, descargarArchivo, postMultipart,
  type FormatoExport,
} from "@/services/api"

/**
 * Traducción filtros → query params. FUENTE ÚNICA del listado y del export.
 *
 * 🔴 Que los dos pasen por acá es lo que hace estructuralmente imposible que un filtro quede
 * en una sola de las dos puntas. El bug clásico es sumar un filtro al listado y que el archivo
 * salga con MÁS filas de las que se ven, sin error y sin aviso.
 */
function queryVacantes(estado?: string): Record<string, string | undefined> {
  return { estado }
}

export async function fetchVacantes(estado?: string, empresaIdOverride?: string): Promise<Vacante[]> {
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(queryVacantes(estado))) {
    if (v) params.set(k, v)
  }
  const query = params.toString() ? `?${params}` : ""
  return apiFetch<Vacante[]>(
    `/api/vacantes${query}`,
    empresaIdOverride ? { headers: { "X-Empresa-Id": empresaIdOverride } } : {},
  )
}

/** Exporta el listado con el MISMO estado y la MISMA empresa que muestra la pantalla. */
export function exportarVacantes(
  formato: FormatoExport, estado?: string, empresaIdOverride?: string,
): Promise<void> {
  return descargarArchivo(
    "/api/vacantes/exportar", formato, "vacantes",
    empresaIdOverride ? { "X-Empresa-Id": empresaIdOverride } : undefined,
    queryVacantes(estado),
  )
}

export async function fetchVacante(id: string): Promise<Vacante> {
  return apiFetch<Vacante>(`/api/vacantes/${id}`)
}

/**
 * Texto listo para pegar en el aviso, con el código de la vacante y la casilla del sistema.
 * Endpoint aparte y no un campo de `Vacante` porque la casilla NO es de la vacante: es una sola
 * para todo el sistema y sale de la integración designada como remitente.
 */
export async function fetchAvisoPostulacion(id: string): Promise<AvisoPostulacion> {
  return apiFetch<AvisoPostulacion>(`/api/vacantes/${id}/aviso`)
}

export async function createVacante(data: VacanteCreate): Promise<Vacante> {
  return apiFetch<Vacante>("/api/vacantes", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function updateVacante(id: string, data: VacanteUpdate): Promise<Vacante> {
  return apiFetch<Vacante>(`/api/vacantes/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  })
}

/** Elimina la vacante y sus imágenes; sus candidatos sobreviven. El endpoint devuelve 204. */
export async function deleteVacante(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/vacantes/${id}`, { method: "DELETE", headers: authHeaders() })
  if (!res.ok) {
    let msg = "No se pudo eliminar la vacante."
    try { msg = ((await res.json()) as { message?: string }).message ?? msg } catch { /* sin body */ }
    throw new ApiError(msg, "UNKNOWN", res.status)
  }
}

export async function fetchCandidatos(vacanteId: string): Promise<Candidato[]> {
  return apiFetch<Candidato[]>(`/api/vacantes/${vacanteId}/candidatos`)
}

export async function createCandidato(
  vacanteId: string,
  data: CandidatoCreate,
  cv?: File | null,
): Promise<Candidato> {
  const form = new FormData()
  form.append("nombre", data.nombre)
  form.append("apellido", data.apellido)
  form.append("email", data.email)
  if (data.cargo_anterior) form.append("cargo_anterior", data.cargo_anterior)
  if (data.empresa_anterior) form.append("empresa_anterior", data.empresa_anterior)
  if (cv) form.append("cv", cv)
  return postMultipart<Candidato>(`/api/vacantes/${vacanteId}/candidatos`, form)
}

export async function moverCandidato(candidatoId: string, etapa: EtapaPipeline): Promise<Candidato> {
  return apiFetch<Candidato>(`/api/candidatos/${candidatoId}/etapa`, {
    method: "PUT",
    body: JSON.stringify({ etapa }),
  })
}

export async function publicarLinkedin(vacanteId: string, data: LinkedinPublicarRequest): Promise<LinkedinPublicarResponse> {
  return apiFetch<LinkedinPublicarResponse>(`/api/vacantes/${vacanteId}/publicar-linkedin`, {
    method: "POST",
    body: JSON.stringify(data),
  })
}

/**
 * Revisa la casilla del sistema: matchea cada mail por el código del asunto y crea los
 * candidatos con su CV. NO recibe vacante: la corrida es sobre la casilla entera y cada mail
 * elige su búsqueda. Reemplaza a fetchEmailsCandidatos + crearCandidatoDesdeEmail.
 */
export async function revisarCasilla(): Promise<IngestaResultado> {
  return apiFetch<IngestaResultado>("/api/vacantes/casilla/revisar", { method: "POST" })
}

/**
 * Mails de la casilla que no matchearon ninguna búsqueda. Se releen de Gmail en cada llamada:
 * no hay estado persistido, la casilla es la fuente de verdad.
 */
export function fetchMailsPendientes(): Promise<MailPendiente[]> {
  return apiFetch<MailPendiente[]>("/api/vacantes/casilla/pendientes")
}

/** Crea los candidatos de un mail sobre la vacante que eligió RRHH. */
export function asignarMail(messageId: string, vacanteId: string): Promise<AsignacionResultado> {
  return apiFetch<AsignacionResultado>("/api/vacantes/casilla/asignar", {
    method: "POST", body: JSON.stringify({ message_id: messageId, vacante_id: vacanteId }),
  })
}
