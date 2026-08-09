/**
 * Clasificador de CVs: el botón y el criterio configurable (migración 100).
 *
 * El criterio se sirve desde `/api/screening/criterio` y no desde `/api/configuracion`, aunque la
 * pantalla que lo edita sea /configuracion: el router es propio porque `vacantes.py` estaba en
 * 80/80 exacto. La URL no tiene por qué coincidir con la ruta de la página.
 */
import { apiFetch } from "@/services/api"
import type { ScreeningCriterio, ScreeningCriterioResponse, ScreeningLoteResponse } from "@/types/screening"
import type { CandidatoConGrupo, ClasificacionIA } from "@/types/candidato"

/**
 * Clasifica los CVs de la vacante que todavía no tienen clasificación.
 *
 * Es REINTENTABLE y no acumula costo: el backend pide `clasificacion_ia IS NULL`, así que
 * apretarlo de nuevo sobre una vacante ya clasificada cuesta cero llamadas. Después de un corte
 * por presupuesto (`parcial`) o por tope (`tope_alcanzado`), volver a apretarlo toma el resto.
 */
export function clasificarPendientes(vacanteId: string): Promise<ScreeningLoteResponse> {
  return apiFetch<ScreeningLoteResponse>(`/api/screening/vacantes/${vacanteId}`, { method: "POST" })
}

/**
 * Corrige a mano la clasificación de un candidato. Queda marcada como HUMANA (`origen`).
 *
 * 🔴 Una vez corregida, ninguna corrida posterior la pisa: el backend solo toma los que tienen
 * `clasificacion_ia IS NULL`. Es lo que hace que corregir valga la pena.
 *
 * El `motivo` es obligatorio: cambiar la etiqueta sin escribir por qué dejaría la fila diciendo
 * `relevante` con el motivo del `no_relevante` anterior.
 */
export function corregirClasificacion(
  candidatoId: string, clasificacion: ClasificacionIA, motivo: string,
): Promise<CandidatoConGrupo> {
  return apiFetch<CandidatoConGrupo>(`/api/screening/candidatos/${candidatoId}/clasificacion`, {
    method: "PUT", body: JSON.stringify({ clasificacion, motivo }),
  })
}

/** Criterio vigente para la empresa activa: el suyo, o el global si no configuró nada. */
export function getCriterioScreening(): Promise<ScreeningCriterioResponse> {
  return apiFetch<ScreeningCriterioResponse>("/api/screening/criterio")
}

/** Guarda el criterio de la empresa activa. Si venía heredando el global, la desengancha. */
export function setCriterioScreening(criterio: ScreeningCriterio): Promise<ScreeningCriterioResponse> {
  return apiFetch<ScreeningCriterioResponse>("/api/screening/criterio", {
    method: "PUT", body: JSON.stringify(criterio),
  })
}

/**
 * Vuelve a heredar el criterio global: borra la fila propia de la empresa.
 *
 * No copia los textos globales a la empresa — si lo hiciera, quedaría `es_propia: true` sobre una
 * foto congelada de los defaults de hoy y un ajuste posterior del global no la alcanzaría.
 */
export function restaurarCriterioScreening(): Promise<ScreeningCriterioResponse> {
  return apiFetch<ScreeningCriterioResponse>("/api/screening/criterio/restaurar", { method: "POST" })
}
