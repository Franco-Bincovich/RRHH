import { apiFetch } from "@/services/api"
import type {
  Configuracion,
  EscalaResponse,
  Parametros,
  ParametrosResponse,
  TramoEscala,
} from "@/types/configuracion"

/** Configuración vigente para la empresa activa (resuelta por COALESCE en el backend). */
export async function fetchConfiguracion(): Promise<Configuracion> {
  return apiFetch<Configuracion>("/api/configuracion")
}

/**
 * Guarda los parámetros de la empresa activa. Es PUT y no PATCH: viaja el juego completo, así
 * no se puede guardar medio set y dejar el resto heredado sin que nadie lo note.
 */
export async function guardarParametros(datos: Parametros): Promise<ParametrosResponse> {
  return apiFetch<ParametrosResponse>("/api/configuracion/parametros", {
    method: "PUT",
    body: JSON.stringify(datos),
  })
}

/**
 * Reemplaza la escala completa. Una lista vacía es un reset explícito: la empresa vuelve a
 * heredar la global (la respuesta lo confirma con `es_propia: false`).
 */
export async function guardarEscala(tramos: TramoEscala[]): Promise<EscalaResponse> {
  return apiFetch<EscalaResponse>("/api/configuracion/escala", {
    method: "PUT",
    body: JSON.stringify({ tramos }),
  })
}
