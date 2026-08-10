/**
 * El token de sesión del link público, guardado en **sessionStorage**.
 *
 * 🔴 POR QUÉ sessionStorage Y NO LAS OTRAS DOS. Se evaluaron las tres:
 *
 *   · MEMORIA PURA (useState) — se pierde con cada F5. El empleado carga varios renglones del
 *     día o de la semana; un refresh accidental lo mandaría a re-tipear el DNI, que es la parte
 *     más frágil del flujo y la que más se equivoca.
 *   · localStorage — sobrevive al cierre de la pestaña y del navegador. En una máquina
 *     COMPARTIDA —que es el escenario real de este link: una PC de planta, un tablet en la
 *     recepción— dejaría la sesión de una persona viva para la siguiente que se siente. El TTL
 *     de 30 minutos del backend acota el daño, pero el front no tiene por qué estirar la
 *     exposición hasta ese techo.
 *   · sessionStorage — sobrevive al refresh y MUERE al cerrar la pestaña. Es exactamente la
 *     duración de una sesión de trabajo, y coincide con el TTL de 30 minutos del backend.
 *
 * ⚠️ NO ES ALMACENAMIENTO SEGURO: cualquier script de la página lo lee. Lo que lo hace tolerable
 * es que el token vale 30 minutos, solo sirve para este link, y lo peor que permite es cargar
 * horas a nombre de una persona y leer su semana. No da acceso a nada más del sistema.
 *
 * Todas las funciones toleran que `sessionStorage` no exista: en el render del servidor de
 * Next NO hay `window`, y tocarlo ahí revienta la página entera.
 */
const CLAVE = "horas-publico-token"

function almacen(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.sessionStorage
  } catch {
    return null // modo privado de algunos navegadores tira al ACCEDER, no al usar
  }
}

export function guardarToken(token: string): void {
  almacen()?.setItem(CLAVE, token)
}

export function leerToken(): string | null {
  return almacen()?.getItem(CLAVE) ?? null
}

export function borrarToken(): void {
  almacen()?.removeItem(CLAVE)
}
