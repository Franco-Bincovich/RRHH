import { describe, expect, it } from "vitest"

import { rolDesactualizado } from "@/services/auth"

/**
 * El front gobernaba con el rol que guardó en el login: a quien se lo bajaban seguía viendo
 * los botones de antes, y cada click terminaba en 403.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * Se prueba la DECISIÓN, no el efecto: vitest corre sin jsdom, así que el `useEffect` del
 * AuthGuard no se ejecuta y un test de componente daría verde con la sincronización borrada
 * (es el caso #4 de "un test solo prueba lo que el fake puede desmentir"). Acá cada caso fija
 * un par (guardado, vigente) distinto, así que colapsar la función a `true`, a `false`, o
 * dejar que el `null` gane rojea en alguno.
 */
describe("rolDesactualizado", () => {
  it("adopta el rol nuevo cuando el backend dice otro", () => {
    expect(rolDesactualizado("admin_rrhh", "gerencia_lectura")).toBe(true)
  })

  it("no toca nada cuando coinciden", () => {
    expect(rolDesactualizado("admin_rrhh", "admin_rrhh")).toBe(false)
  })

  it("🔴 null NO es 'se quedó sin rol': el backend no pudo resolverlo", () => {
    // Adoptarlo dejaría al usuario sin permisos en el front por un blip de base — una app
    // vacía en vez de la suya, y encima sin ningún error a la vista.
    expect(rolDesactualizado("admin_rrhh", null)).toBe(false)
  })

  it("también detecta la subida de rol, no solo la bajada", () => {
    expect(rolDesactualizado("mandos_medios", "admin_rrhh")).toBe(true)
  })
})
