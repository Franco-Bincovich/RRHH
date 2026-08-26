/**
 * La forma del código de la búsqueda, del lado del navegador.
 *
 * 🔴 ES UN ESPEJO DE `backend/services/_vacante_codigo.py`, Y ESTÁ DECLARADO COMO TAL. La
 * autoridad es el backend —y detrás suyo el CHECK de la migración 122—: si estas dos reglas
 * divergen, la que decide es la de allá y acá sólo cambia si el error llega antes o después de
 * viajar. Existe igual porque un código mal escrito es de los errores que más se cometen (se
 * tipea a mano, una vez, y después se pega en un aviso) y esperar el round-trip para enterarse
 * de que sobraba un espacio es exactamente lo que §3 pide evitar.
 *
 * ⚠️ Lo que este archivo NO hace, a propósito: chequear la UNICIDAD. Eso requiere mirar todas las
 * vacantes del sistema —incluidas las de otras empresas— y sólo la base puede contestarlo sin
 * mentir. El front no adivina: manda y muestra el mensaje del backend, que además nombra la
 * búsqueda que ya tiene ese código.
 *
 * Hay un test EN EL BACKEND (`tests/test_vacante_codigo_unico.py`) que abre este archivo y
 * verifica que las tres reglas sigan diciendo lo mismo. El viaje va en esa dirección porque el
 * backend es el que manda — mismo criterio que `test_espejo_permisos.py`.
 */

export const CODIGO_MIN = 3
export const CODIGO_MAX = 30

/** Letras, dígitos y guion como separador. Sin guion al principio, al final, ni dos seguidos. */
const FORMA = /^[A-Z0-9]+(-[A-Z0-9]+)*$/

/**
 * El código en su forma canónica: MAYÚSCULAS y un guion como único separador.
 * `eco 2026`, ` ECO_2026 ` y `eco--2026` son la misma búsqueda.
 */
export function normalizarCodigo(valor: string): string {
  return valor.trim().toUpperCase().replace(/[\s._-]+/g, "-").replace(/^-+|-+$/g, "")
}

/**
 * El mensaje de error del campo, o `undefined` si el código sirve.
 *
 * 🔑 El mensaje dice QUÉ CORREGIR y muestra un ejemplo usable, no "formato inválido": quien lo
 * está escribiendo por primera vez no tiene de dónde deducir la regla.
 */
export function validarCodigo(valor: string): string | undefined {
  const codigo = normalizarCodigo(valor)
  if (!codigo) return "El código es requerido: es lo que el candidato pone en el asunto del mail (ej. ECO-2026)"
  if (codigo.length < CODIGO_MIN) return `Muy corto: mínimo ${CODIGO_MIN} caracteres (ej. ECO-2026)`
  if (codigo.length > CODIGO_MAX) return `Muy largo: máximo ${CODIGO_MAX} caracteres`
  // Antes que la forma general: "sólo números" es el error que más ayuda explicar, porque el
  // código parece un número de búsqueda y el motivo del rechazo no es evidente.
  if (!/[A-Z]/.test(codigo)) return "Necesita al menos una letra (ej. ECO-2026): un código de puros números matchearía cualquier año suelto en el asunto"
  if (!FORMA.test(codigo)) return "Usá sólo letras, números y guiones, sin acentos ni símbolos (ej. ECO-2026)"
  return undefined
}
