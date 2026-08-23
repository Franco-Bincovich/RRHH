import { ApiError } from "@/services/api"

/**
 * Lo puro del bloque "Mails sin asignar": qué se muestra, y qué se dice cuando falla.
 *
 * 🔴 EXISTE PARA PODER TESTEARLO. `vitest` corre con `environment: "node"` y sin jsdom, así que
 * los tests de componente usan `renderToStaticMarkup` y **no ejecutan `useEffect`**: lo único que
 * se puede renderizar de `MailsPendientes` es su estado inicial (el esqueleto). La decisión que
 * este archivo aísla —la que tenía el bug— es inalcanzable desde ahí. Mismo criterio que
 * `vacanteForm.ts` y que `components/features/horasPublico/logica.ts`.
 */

/** Qué ocupa el cuerpo del bloque. Los tres son excluyentes. */
export type Vista = "error" | "vacio" | "lista"

/**
 * 🔴 UN ERROR DE LECTURA GANA SOBRE "NO HAY NADA", SIEMPRE.
 *
 * El bug que esto cierra: cuando la casilla del sistema perdió el acceso a Google, la pantalla
 * mostraba el error **y debajo** "No hay mails con adjuntos esperando asignación" — o sea que
 * afirmaba que el buzón estaba vacío justo cuando no lo había podido leer. Con mails de verdad
 * esperando, eso es peor que un error: es una respuesta falsa a la pregunta que RRHH vino a
 * hacer. La lista se relee de Gmail en cada carga (no hay estado persistido), así que sin
 * lectura no hay NADA que afirmar sobre el buzón.
 */
export function vista(errorCasilla: string | null, cantidadMails: number): Vista {
  if (errorCasilla) return "error"
  return cantidadMails === 0 ? "vacio" : "lista"
}

/**
 * Qué se le muestra a RRHH cuando la casilla no se pudo leer.
 *
 * 🔑 EL MENSAJE DEL BACKEND SE RESPETA TAL CUAL, y es lo que hace que sirva: desde el arreglo
 * del 23/8/2026 esos mensajes dicen QUÉ HACER —"Reconectala desde Configuración → Integraciones"
 * si Google revocó el permiso, "Reintentá en unos minutos" si fue un problema de red— y son dos
 * acciones distintas que el front no puede adivinar. Reemplazarlos por un genérico tiraría justo
 * lo único accionable. Mismo criterio que `services/horasPublico.ts`.
 *
 * El fallback es para lo que NO llegó a ser una respuesta del backend (sin internet, el servidor
 * caído): ahí el backend no dijo nada y hay que decir algo igual.
 */
export function mensajeDeCasilla(e: unknown): string {
  if (e instanceof ApiError) return e.message
  return "No se pudo contactar al servidor para leer la casilla. Revisá tu conexión y reintentá."
}
