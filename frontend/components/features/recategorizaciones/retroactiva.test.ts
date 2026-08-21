import { describe, expect, it } from "vitest"

import type { Recategorizacion } from "@/types/recategorizacion"

import {
  TEXTO_AVISO_RETROACTIVO, avisoRetroactivo, ultimaFechaEfectiva,
} from "./_retroactiva"

/**
 * (b) el aviso de fecha retroactiva.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * La regla tiene TRES resultados posibles y los tres están acá, cada uno con un caso propio:
 * anterior → avisa · igual → NO avisa · posterior → NO avisa. Con solo el primero, una función
 * que devolviera `true` siempre pasaría; con solo los últimos dos, una que devolviera `false`
 * siempre también. **El caso "igual" es el que más fácil se escribe mal**: un `<=` en vez de un
 * `<` haría que cargar dos recategorizaciones el mismo día avise que el legajo no se toca,
 * cuando el backend sí lo pisa — o sea, la pantalla mintiendo en la dirección contraria.
 *
 * Y el caso "no hay ninguna previa" está aparte del resto porque es el estado de producción hoy:
 * con 0 filas cargadas, TODA alta es la primera, y un aviso ahí sería puro ruido en el 100% de
 * los usos del módulo desde el día uno.
 */

const fila = (fecha: string): Recategorizacion =>
  ({ id: fecha, fecha_efectiva: fecha } as Recategorizacion)

describe("(b) el aviso aparece solo si la fecha queda ATRÁS en la cadena", () => {
  it("🔴 con una fecha ANTERIOR a la última, avisa", () => {
    // Es el caso real: se carga una del 1/8 habiendo una del 1/9. El histórico se registra y el
    // legajo NO cambia, porque el rol vigente lo fijó la de septiembre.
    expect(avisoRetroactivo("2026-08-01", "2026-09-01")).toBe(true)
  })

  it("con la fecha de HOY (posterior a la última), no avisa", () => {
    expect(avisoRetroactivo("2026-09-20", "2026-09-01")).toBe(false)
  })

  it("🔴 con la fecha IGUAL a la última, TAMPOCO avisa", () => {
    // El backend la trata como la más reciente y sí pisa el legajo. Avisar acá sería mentir, y
    // es lo que pasaría con un `<=` en lugar de un `<`.
    expect(avisoRetroactivo("2026-09-01", "2026-09-01")).toBe(false)
  })

  it("sin ninguna recategorización previa, no avisa: ésta ES la más reciente", () => {
    // El estado de producción hoy (0 filas): avisar sería ruido en el 100% de las altas.
    expect(avisoRetroactivo("2026-01-01", null)).toBe(false)
  })

  it("sin fecha elegida tampoco avisa: no hay nada que comparar todavía", () => {
    expect(avisoRetroactivo("", "2026-09-01")).toBe(false)
  })
})

describe("cuál es la última de la cadena", () => {
  it("toma la MÁXIMA, no la primera del array", () => {
    // El backend devuelve el historial ordenado, pero de esta decisión depende lo que la
    // pantalla AFIRMA: si algún día cambia el orden, un `[0]` empezaría a comparar contra la
    // fila equivocada sin ningún error visible.
    expect(ultimaFechaEfectiva([fila("2026-03-01"), fila("2026-09-01"), fila("2026-05-01")]))
      .toBe("2026-09-01")
  })

  it("sin historial devuelve null, que es lo que apaga el aviso", () => {
    expect(ultimaFechaEfectiva([])).toBeNull()
  })
})

describe("el texto del aviso", () => {
  it("dice las DOS mitades: que se registra Y que el legajo no cambia", () => {
    // La primera mitad sola sonaría a error; la segunda sola, a que no se guardó nada.
    expect(TEXTO_AVISO_RETROACTIVO).toContain("registrar")
    expect(TEXTO_AVISO_RETROACTIVO).toContain("NO va a cambiar")
  })

  it("y no habla de aprobación ni de porcentajes (§7)", () => {
    expect(TEXTO_AVISO_RETROACTIVO).not.toContain("aprob")
    expect(TEXTO_AVISO_RETROACTIVO).not.toContain("%")
  })
})
