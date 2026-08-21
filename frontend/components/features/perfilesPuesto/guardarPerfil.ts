import { ApiError } from "@/services/api"
import { createPerfil, updatePerfil } from "@/services/perfilesPuesto"
import type { CampoPerfil, PerfilPuesto, PerfilPuestoCreate } from "@/types/perfilPuesto"

import { armarPayload } from "./_perfilCampos"

/**
 * La decisión de guardar un perfil: validar primero y mandar SOLO si pasa.
 *
 * 🔴 POR QUÉ VIVE ACÁ Y NO EN EL CUERPO DE `PerfilModal`. El modal monta por PORTAL (`Dialog` de
 * base-ui): con vitest sin jsdom, `renderToStaticMarkup(<PerfilModal/>)` devuelve `""`, así que
 * un test de ese componente pasaría con el formulario entero borrado. La decisión que hay que
 * poder desmentir tiene que ser una función suelta. Molde: `guardarCliente.ts`.
 */

/** El tope es de PRODUCTO, no de base: `perfiles_puesto.nombre` es `text` sin límite. El nombre
 *  se muestra entero en el selector de vacantes y en el título del aviso que lo copia; más que
 *  esto no se lee. Espejo de `MAX_NOMBRE` de `schemas/perfil_puesto.py`. */
export const MAX_NOMBRE = 120

export interface ErroresPerfil {
  nombre?: string
}

/**
 * Errores del formulario. Objeto vacío = se puede mandar.
 *
 * 🔴 SOLO SE VALIDA EL NOMBRE, y los otros once campos NO son un olvido. Exigirlos llenos sería
 * peor que no exigir nada: un perfil legítimo puede no pedir formación académica, y el rechazo
 * enseñaría a escribir cualquier cosa para pasar el validador. Es la misma decisión que el
 * backend ya tomó y dejó escrita en `_perfil_puesto_campos.py` — "NO HAY VALIDACIÓN QUE SUSTITUYA
 * ESTO": lo único que evita que los cuatro campos de requisitos se llenen mal son los textos de
 * ayuda, mostrados ANTES de escribir.
 */
export function validarPerfil(valores: Record<string, string>): ErroresPerfil {
  const nombre = (valores.nombre ?? "").trim()
  if (!nombre) return { nombre: "El nombre del perfil es requerido" }
  if (nombre.length > MAX_NOMBRE) return { nombre: `Máximo ${MAX_NOMBRE} caracteres` }
  return {}
}

/**
 * Valida y guarda. Alta o edición según venga `perfil`.
 *
 * El body se arma RECORRIENDO los campos que devolvió el endpoint (`armarPayload`), no con una
 * lista escrita acá: un campo nuevo en el backend viaja solo.
 *
 * @returns Los errores si NO guardó, o `null` si guardó. Un `AppError` del backend
 *   (PERFIL_DUPLICADO 409, NOMBRE_REQUERIDO 422) sale como excepción y lo traduce `mensajeDeError`.
 */
export async function guardarPerfil(
  valores: Record<string, string>, campos: CampoPerfil[], perfil?: PerfilPuesto,
): Promise<ErroresPerfil | null> {
  const errores = validarPerfil(valores)
  if (Object.keys(errores).length > 0) return errores
  const body = armarPayload(valores, campos)
  if (perfil) await updatePerfil(perfil.id, body)
  else await createPerfil(body as PerfilPuestoCreate)
  return null
}

/**
 * Mensaje a mostrar cuando falla un alta o una edición.
 *
 * 🔴 EL MENSAJE DEL BACKEND SE CONSERVA TAL CUAL. El error de negocio que este formulario produce
 * de verdad es `PERFIL_DUPLICADO` (409), y su texto no es genérico: dice **por qué** el nombre
 * choca aunque el perfil se vea distinto — *"Los perfiles son de todo el grupo, así que el nombre
 * tiene que ser único en el sistema entero, no por empresa"*. Es exactamente el dato que a alguien
 * de Capital Humano le falta para entender qué pasó, porque contradice cómo funciona el resto del
 * sistema. Reemplazarlo por "No se pudo guardar" deja a la persona probando el mismo nombre otra
 * vez, y "Intentá de nuevo" es además el consejo equivocado: reintentar nunca va a funcionar.
 *
 * El genérico queda SOLO para lo que no es un error de la API (red caída, timeout), donde
 * reintentar sí es lo razonable.
 */
export function mensajeDeError(e: unknown): string {
  return e instanceof ApiError ? e.message : "No se pudo guardar. Intentá de nuevo."
}
