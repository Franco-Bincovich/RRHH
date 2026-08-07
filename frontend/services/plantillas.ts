import { apiFetch } from "@/services/api"
import type { EnvioResponse, Plantilla, PlantillasResponse, PreviewResponse } from "@/types/plantillas"

const BASE = "/api/plantillas"

/** Plantillas visibles para la empresa activa + el catálogo de contextos y sus variables. */
export async function fetchPlantillas(): Promise<PlantillasResponse> {
  return apiFetch<PlantillasResponse>(BASE)
}

/**
 * Crea o edita. Siempre escribe la versión de la empresa activa: editar una global desde acá
 * NO la cambia para las demás empresas, crea la propia. Esa decisión vive en el backend.
 */
export async function guardarPlantilla(
  body: Partial<Plantilla> & { clave: string; contexto: string; asunto: string; cuerpo: string },
): Promise<Plantilla> {
  return apiFetch<Plantilla>(BASE, { method: "PUT", body: JSON.stringify(body) })
}

export async function borrarPlantilla(id: string): Promise<void> {
  return apiFetch<void>(`${BASE}/${id}`, { method: "DELETE" })
}

/**
 * Previsualiza SIN enviar, con el mismo renderer que usa el envío.
 * `empleadoId` ausente → datos de ejemplo. Con un empleado real se ven los huecos reales, que
 * es el punto: con datos inventados, un área sin cargar no se nota.
 */
export async function previewPlantilla(
  body: { contexto: string; asunto: string; cuerpo: string; empleado_id?: string },
): Promise<PreviewResponse> {
  return apiFetch<PreviewResponse>(`${BASE}/preview`, { method: "POST", body: JSON.stringify(body) })
}

/**
 * Manda la plantilla a los empleados elegidos. Es lo único irreversible de este módulo.
 *
 * 🔴 La respuesta NO es un ok/error: son cinco números (ver `EnvioResponse`). El backend manda
 * de a uno con presupuesto de tiempo, así que un 200 puede significar "salieron 30 de 50".
 * Quien la llame tiene que mostrar el desglose — un "Enviado" a secas sería mentira.
 *
 * ⚠️ La empresa viaja por el header `X-Empresa-Id` que pone `apiFetch`, y NO es un detalle:
 * el backend resuelve con ella QUÉ plantilla usa (la de la empresa o la global). En modo
 * consolidado el header es "todas" → el backend solo encuentra la GLOBAL, así que la pantalla
 * exige una empresa elegida antes de dejar enviar (ver `useEnvioPlantilla`).
 */
export async function enviarPlantilla(
  plantillaClave: string,
  empleadoIds: string[],
): Promise<EnvioResponse> {
  return apiFetch<EnvioResponse>(`${BASE}/enviar`, {
    method: "POST",
    body: JSON.stringify({ plantilla_clave: plantillaClave, empleado_ids: empleadoIds }),
  })
}
