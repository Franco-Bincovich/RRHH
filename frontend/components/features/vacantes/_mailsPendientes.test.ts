import { describe, expect, it } from "vitest"

import { mensajeDeCasilla, vista } from "@/components/features/vacantes/_mailsPendientes"
import { ApiError } from "@/services/api"

/**
 * Qué muestra el bloque "Mails sin asignar" cuando la casilla no se puede leer.
 *
 * 🔴 EL BUG QUE CIERRA: con la casilla del sistema sin acceso a Google, la pantalla mostraba el
 * error **y debajo** "No hay mails con adjuntos esperando asignación". O sea que afirmaba que el
 * buzón estaba vacío justo cuando no lo había podido abrir — con mails de verdad esperando.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *   · El caso decisivo es **error + CERO mails**, que es exactamente el estado real cuando la
 *     lectura falla (el `catch` deja `mails` en []). Probar solo "error + 3 mails" pasaría con
 *     la precedencia dada vuelta, porque ahí `vacio` no compite.
 *   · Los mensajes se comparan por lo que el backend mandó, no contra una constante del propio
 *     módulo: comparar con la constante sería afirmar que una variable es igual a sí misma.
 */

describe("🔴 un error de lectura gana sobre «no hay nada»", () => {
  it("con la casilla caída y cero mails muestra el ERROR, no el vacío", () => {
    // El caso real: `cargar` falló, así que `mails` quedó en []. Si `vacio` ganara, la pantalla
    // diría "no hay mails" sin haber podido leer el buzón. Ese era el bug, literal.
    expect(vista("La casilla perdió el acceso a Google.", 0)).toBe("error")
  })

  it("con la casilla caída y mails viejos en pantalla también muestra el error", () => {
    expect(vista("La casilla perdió el acceso a Google.", 3)).toBe("error")
  })
})

describe("sin error, la vista la decide cuántos mails hay", () => {
  it("cero mails es el estado vacío", () => {
    expect(vista(null, 0)).toBe("vacio")
  })

  it("con mails se muestra la lista", () => {
    expect(vista(null, 1)).toBe("lista")
  })
})

describe("el mensaje dice QUÉ HACER", () => {
  it("respeta el mensaje del backend, que es el único que sabe si hay que reconectar", () => {
    const delBackend = "La casilla del sistema perdió el acceso a Google. Reconectala desde Configuración → Integraciones."
    expect(mensajeDeCasilla(new ApiError(delBackend, "GMAIL_TOKEN_EXPIRED", 502))).toBe(delBackend)
  })

  it("y también cuando el backend dice que hay que esperar, que es la acción OPUESTA", () => {
    const delBackend = "No se pudo contactar a Google para renovar el acceso de la casilla del sistema. Reintentá en unos minutos."
    expect(mensajeDeCasilla(new ApiError(delBackend, "GMAIL_RENOVACION_FALLIDA", 502))).toBe(delBackend)
  })

  it("si no hubo respuesta del backend, dice algo accionable igual", () => {
    // Un `TypeError` es lo que tira `fetch` sin internet: no hay `message` que mostrarle a nadie
    // ("Failed to fetch" no es un mensaje para RRHH).
    const texto = mensajeDeCasilla(new TypeError("Failed to fetch"))
    expect(texto).toContain("conexión")
    expect(texto).not.toContain("Failed to fetch")
  })
})
