/**
 * La conversión del código de la búsqueda, del lado del navegador.
 *
 * 🔴 CAPITAL HUMANO ESCRIBE TEXTO NATURAL Y ACÁ SE CONVIERTE, EN VIVO. `"Lider de equipo"` →
 * `LIDER-DE-EQUIPO`. La pantalla muestra el resultado debajo del campo mientras se escribe
 * (`VacanteCampoCodigo`, "Se va a usar: …") y ésa es la razón de que esta función esté acá y no
 * sólo en el backend: **convertir en silencio sería peor que rechazar**. Escriben una cosa, el
 * sistema guarda otra, y se enteran cuando el candidato pregunta por qué su CV no llegó.
 *
 * 🔴 ES UN ESPEJO DE `backend/services/_vacante_codigo.py`, Y ESTÁ DECLARADO COMO TAL. La
 * autoridad es el backend —y detrás suyo el CHECK de las migraciones 122/123—: si las reglas
 * divergen, la que decide es la de allá. Hay un test EN EL BACKEND
 * (`tests/test_vacante_codigo_unico.py`) que abre este archivo y verifica que sigan diciendo lo
 * mismo; el viaje va en esa dirección porque el backend es el que manda, mismo criterio que
 * `test_espejo_permisos.py`.
 *
 * ⚠️ Lo que este archivo NO hace, a propósito: chequear la UNICIDAD. Eso requiere mirar todas las
 * vacantes del sistema —incluidas las de otras empresas— y sólo la base puede contestarlo sin
 * mentir. El front no adivina: manda y muestra el mensaje del backend, que además nombra la
 * búsqueda que ya tiene ese código.
 */

export const CODIGO_MIN = 3
/** 60 y no 30: "Analista de Sistemas Semi Senior" —una vacante real— canoniza a 32. Ver la mig 123. */
export const CODIGO_MAX = 60

/** Letras, dígitos y guion como separador. La conversión no puede producir otra forma. */
const FORMA = /^[A-Z0-9]+(-[A-Z0-9]+)*$/

/**
 * El texto convertido a código, SIN validar. `""` si no queda nada utilizable.
 *
 * Las dos reglas, y son las mismas que las del backend:
 *   · **sin acentos ni ñ** — `Ecónomo` → `ECONOMO`, `Diseño` → `DISENO`. El código termina en el
 *     asunto de un mail que se tipea desde el teléfono, donde una tilde se escribe mal la mitad
 *     de las veces. (El matcher le saca los acentos AL ASUNTO con la misma regla, así que un
 *     candidato que escriba `Ecónomo 2026` matchea igual.)
 *   · **todo lo que no es letra ni dígito es separador**, y un run de separadores es UN guion.
 */
export function normalizarCodigo(valor: string): string {
  return valor
    .trim()
    .normalize("NFD")
    .replace(/\p{Mn}/gu, "")     // las marcas diacríticas que quedaron sueltas al descomponer
    .toUpperCase()
    .replace(/[^A-Z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
}

/**
 * El mensaje de error del campo, o `undefined` si el texto sirve.
 *
 * 🔑 Todo mensaje habla del CÓDIGO RESULTANTE, no del texto tipeado, y dice qué hacer: el usuario
 * ve la conversión debajo del campo, así que decirle "«LI» es muy corto" es lo que conecta lo que
 * escribió con lo que el sistema entendió.
 */
export function validarCodigo(valor: string): string | undefined {
  const codigo = normalizarCodigo(valor)
  if (!codigo) return "El código es requerido: escribí un nombre con letras o números, por ejemplo «Líder de equipo»"
  if (codigo.length < CODIGO_MIN) return `«${codigo}» es muy corto: necesita al menos ${CODIGO_MIN} caracteres, o va a matchear cualquier palabra de un asunto`
  // Antes que la forma general: "sólo números" es el error que más ayuda explicar, porque el
  // código parece un número de búsqueda y el motivo del rechazo no es evidente.
  if (!/[A-Z]/.test(codigo)) return `«${codigo}» no tiene ninguna letra: un código de puros números matchea cualquier año suelto en el asunto de un mail`
  // 🔴 RECHAZA, NO RECORTA. Dos títulos distintos que empiecen igual recortados al mismo largo
  // darían EL MISMO código, y la segunda búsqueda se rechazaría como duplicada de una que su
  // autor nunca escribió. Ver el mismo comentario en `_vacante_codigo.normalizar`.
  if (codigo.length > CODIGO_MAX) return `El código queda en ${codigo.length} caracteres y el máximo es ${CODIGO_MAX}: acortá el texto ${codigo.length - CODIGO_MAX} caracteres`
  if (!FORMA.test(codigo)) return "Usá letras, números y espacios (ej. Líder de equipo)"
  return undefined
}
