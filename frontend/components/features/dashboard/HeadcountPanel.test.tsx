import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import type { HeadcountArea } from "@/services/dashboard"
import { HeadcountPanel } from "./HeadcountPanel"

/**
 * La card de headcount: PLEGADA al entrar, y plegada no muestra ni una fila — solo el título y
 * el contador con el total de áreas.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. El acordeón real no monta el panel plegado, así que "no asoma ninguna área" se afirma por
 *    AUSENCIA de los nombres en el markup. Con un acordeón mockeado que renderice sus children
 *    siempre, las 12 áreas saldrían y el plegado podría estar borrado sin que nada rojee.
 * 2. Los nombres van con dos dígitos ("Área 01"): con "Área 1", buscar la 1 encontraría la 10 y
 *    la aserción de ausencia sería imposible de fallar en un sentido y falsa en el otro.
 * 3. El contador NO se busca como número suelto en el markup —cualquier clase de Tailwind trae
 *    dígitos—: se extrae del chip pegado al <h2> y el helper devuelve null si esa estructura
 *    deja de existir, cosa que cada test afirma antes de comparar.
 *
 * La mitad "desplegada SÍ muestra todo" vive en ConfigSection.test.tsx, que es donde está el
 * mecanismo: acá el Root no es parametrizable y sin jsdom no hay click.
 */

function areas(n: number): HeadcountArea[] {
  return Array.from({ length: n }, (_, i) => ({
    area_id: `id-${i}`,
    area: `Área ${String(i + 1).padStart(2, "0")}`,
    total: 100 - i, // distintos entre sí, y ninguno choca con el contador del encabezado
  }))
}

const render = (n: number) => renderToStaticMarkup(<HeadcountPanel areas={areas(n)} />)

function contador(html: string): string | null {
  const m = html.match(/<h2[^>]*>Headcount por área<\/h2><span[^>]*>([^<]*)<\/span>/)
  return m ? m[1] : null
}

describe("plegada al entrar", () => {
  it("no asoma NINGUNA área, ni la primera", () => {
    // Es el cambio que motivó sacar el preview: con 6 filas asomando la card ocupaba casi lo
    // mismo plegada que abierta, así que el acordeón no recuperaba nada de pantalla.
    const html = render(12)
    const todas = areas(12)
    expect(todas.length).toBeGreaterThan(0) // guarda: sin áreas el forEach no compara nada
    todas.forEach((a) => expect(html).not.toContain(a.area))
  })

  it("pero sí el título y el contador", () => {
    const html = render(12)
    expect(html).toContain("Headcount por área")
    expect(contador(html)).toBe("12")
  })

  it("y ofrece desplegar", () => {
    expect(render(12)).toContain("group-data-panel-open:rotate-180")
  })
})

describe("contador", () => {
  it("es el total de áreas, que es lo único que se ve sin abrir", () => {
    expect(contador(render(12))).toBe("12")
    expect(contador(render(3))).toBe("3")
  })

  it("con cero áreas muestra 0, no se esconde", () => {
    expect(contador(render(0))).toBe("0")
  })
})

describe("card vacía", () => {
  /**
   * ⚠️ EL "Sin datos de headcount." NO SE VERIFICA ACÁ, Y NO SE FINGE QUE SÍ.
   *
   * Vive en el panel, esta card arranca plegada, y el panel plegado no se monta — así que en
   * el markup no está. Un `not.toContain(...)` pasaría trivialmente y un `toContain(...)`
   * fallaría siempre: ninguna de las dos afirma que el mensaje siga existiendo. Y no se puede
   * abrir desde afuera porque el <Accordion.Root> lo pone el propio componente.
   *
   * Lo que sí queda cubierto: que el panel muestre su empty state cuando está abierto se
   * verifica en AlertasPanel.test.tsx —misma shell, mismo patrón, y esa card SÍ arranca
   * abierta—, y que el panel cerrado esconde su contenido, en ConfigSection.test.tsx.
   * Lo único propio de este caso es lo de abajo.
   */
  it("con cero áreas la card sigue entera: título, contador en 0 y desplegable", () => {
    const html = render(0)
    expect(html).toContain("Headcount por área")
    expect(contador(html)).toBe("0")
    expect(html).toContain("group-data-panel-open:rotate-180")
  })
})
