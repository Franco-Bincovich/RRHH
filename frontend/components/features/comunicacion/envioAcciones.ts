import { enviarPlantilla } from "@/services/plantillas"
import type { EnvioResponse } from "@/types/plantillas"

/** Lo mínimo que el envío necesita de un empleado. Un subconjunto de `Empleado`, a propósito:
 *  así el módulo se puede testear con tres objetos de tres campos y no con la ficha entera. */
export interface Destinatario {
  id: string
  nombre: string
  apellido: string
  email_corporativo: string
}

export type ResultadoEnvio =
  | { ok: true; res: EnvioResponse }
  | { ok: false; error: string }

export const ERROR_ENVIO = "No se pudo enviar. Revisá la conexión y probá de nuevo."

/**
 * Los ids que se van a mandar: los SELECCIONADOS, no la lista entera.
 *
 * 🔴 ESTA FUNCIÓN RECIBE LAS DOS COSAS —el catálogo completo y la selección— justamente para que
 * "manda a todos" sea un desenlace POSIBLE y por lo tanto testeable. Si recibiera solo los ids
 * elegidos, un test no podría distinguir un filtro correcto de la ausencia de filtro: no habría
 * nadie de más a quien mandarle. Es la pregunta del repo ("¿qué tendría que ser distinto en el
 * fake para que el test falle?") aplicada al diseño y no al test.
 *
 * Se filtra sobre `empleados` y no se vuelca la Set directo para que el orden y la pertenencia
 * salgan del catálogo: un id que quedó seleccionado y después desapareció del listado (cambió el
 * filtro, se dio de baja) no viaja.
 */
export function destinatarios(empleados: Destinatario[], sel: Set<string>): string[] {
  return empleados.filter((e) => sel.has(e.id)).map((e) => e.id)
}

/**
 * Manda de verdad. Nunca lanza: devuelve el resultado o el mensaje de error ya redactado.
 *
 * Con cero seleccionados NO llama al backend y devuelve error: la UI ya deshabilita el botón,
 * pero un envío vacío que llega igual gastaría uno de los 20 pedidos por hora del rate limit.
 */
export async function enviarAhora(
  clave: string,
  empleados: Destinatario[],
  sel: Set<string>,
  libres: string[] = [],
): Promise<ResultadoEnvio> {
  // Los dos modos son EXCLUYENTES (ver `ModoEnvio`): `libres` con contenido significa modo libre
  // y la selección de empleados no viaja. El backend además rechaza el body mixto (422).
  const ids = libres.length > 0 ? [] : destinatarios(empleados, sel)
  if (ids.length === 0 && libres.length === 0) {
    return { ok: false, error: "Elegí al menos una persona." }
  }
  try {
    return { ok: true, res: await enviarPlantilla(clave, ids, libres) }
  } catch (e) {
    // El backend tiene mensajes accionables para este flujo (sin casilla de sistema configurada,
    // plantilla inexistente, 429 del rate limit). Se muestran tal cual: son más útiles que
    // cualquier texto genérico que pongamos acá.
    return { ok: false, error: e instanceof Error && e.message ? e.message : ERROR_ENVIO }
  }
}
