import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { Historial, type EntradaHistorial } from "@/components/ui/Historial"

/**
 * (f) El chip "Vigente" va en UNO solo: el más reciente.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE PUEDA FALLAR? El test cuenta las apariciones del
 * chip, no su presencia: marcar todos —el error obvio si la decisión se delegara al llamador—
 * pasa cualquier `toContain` y rojea acá.
 */

const ENTRADAS: EntradaHistorial[] = [
  { clave: "b", fecha: "Marzo 2026", desde: "$100.000", hasta: "$120.000", detalle: "neto $96.000" },
  { clave: "a", fecha: "Enero 2026", desde: null, hasta: "$100.000", detalle: "neto $80.000" },
]

describe("(f) el chip Vigente", () => {
  const html = renderToStaticMarkup(<Historial entradas={ENTRADAS} vacio="sin datos" />)

  it("aparece UNA sola vez con dos registros", () => {
    expect(html.match(/Vigente/g) ?? []).toHaveLength(1)
  })

  it("va en el más reciente, que es el primero de la lista", () => {
    expect(html.indexOf("Vigente")).toBeGreaterThan(html.indexOf("Marzo 2026"))
    expect(html.indexOf("Vigente")).toBeLessThan(html.indexOf("Enero 2026"))
  })

  it("con un solo registro también aparece una vez", () => {
    const uno = renderToStaticMarkup(<Historial entradas={[ENTRADAS[0]]} vacio="sin datos" />)
    expect(uno.match(/Vigente/g) ?? []).toHaveLength(1)
  })
})

describe("la forma del historial es lista, no tabla", () => {
  const html = renderToStaticMarkup(<Historial entradas={ENTRADAS} vacio="sin datos" />)

  it("no hay <table> por ningún lado", () => {
    expect(html).not.toContain("<table")
    expect(html).toContain('role="list"')
  })

  it("el registro con 'desde' muestra los dos valores y la flecha", () => {
    expect(html).toContain("$100.000")
    expect(html).toContain("$120.000")
    expect(html).toContain('aria-label="cambia a"')
  })

  it("el registro más viejo NO inventa un 'de'", () => {
    // Es el primero de la serie: no hay valor anterior. Una flecha ahí afirmaría un cambio que
    // no ocurrió — hay una sola flecha para dos registros.
    expect(html.match(/aria-label="cambia a"/g) ?? []).toHaveLength(1)
  })

  it("sin entradas muestra el texto de vacío y ninguna lista", () => {
    const vacio = renderToStaticMarkup(<Historial entradas={[]} vacio="Todavía no hay sueldos cargados." />)
    expect(vacio).toContain("Todavía no hay sueldos cargados.")
    expect(vacio).not.toContain('role="list"')
  })
})
