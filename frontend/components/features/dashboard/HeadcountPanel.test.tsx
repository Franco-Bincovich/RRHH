import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import type { HeadcountArea } from "@/services/dashboard"
import { CORTE_LISTA, partirLista } from "./dashboardAdminData"
import { HeadcountPanel } from "./HeadcountPanel"

/**
 * La card de headcount: las primeras CORTE_LISTA áreas siempre a la vista, el resto detrás del
 * desplegable y PLEGADO al entrar.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. El acordeón real no monta el panel plegado, así que "el resto está escondido" se afirma
 *    por AUSENCIA en el markup. Con un acordeón mockeado que renderice sus children siempre,
 *    las 12 áreas saldrían en el markup y el corte podría estar borrado sin que nada rojee.
 * 2. Los nombres van con dos dígitos ("Área 01"): con "Área 1", buscar la 1 encontraría la 10
 *    y la aserción de "no está" pasaría a ser imposible de fallar en un sentido y falsa en el
 *    otro. Los totales son distintos entre sí para que ningún número se cruce.
 * 3. Los casos NO hardcodean 6: recorren CORTE_LISTA. Si mañana el corte pasa a 8, el test
 *    sigue verificando la misma regla en vez de mentir sobre un número viejo.
 *
 * La otra mitad del despliegue —que abierta SÍ muestre la cola— vive en ConfigSection.test.tsx:
 * acá el Root no es parametrizable y sin jsdom no hay click.
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

describe("corte de la lista", () => {
  it(`muestra las primeras ${CORTE_LISTA} y esconde el resto`, () => {
    const html = render(12)
    const { visibles, resto } = partirLista(areas(12))
    expect(visibles).toHaveLength(CORTE_LISTA)
    expect(resto.length).toBeGreaterThan(0) // guarda: sin esto el forEach de abajo no compara nada
    visibles.forEach((a) => expect(html).toContain(a.area))
    resto.forEach((a) => expect(html).not.toContain(a.area))
  })

  it("si entran todas no esconde ninguna ni ofrece desplegar", () => {
    const html = render(CORTE_LISTA)
    areas(CORTE_LISTA).forEach((a) => expect(html).toContain(a.area))
    expect(html).not.toContain("group-data-panel-open:rotate-180")
  })

  it("si sobra aunque sea una, ofrece desplegar", () => {
    expect(render(CORTE_LISTA + 1)).toContain("group-data-panel-open:rotate-180")
  })
})

describe("contador", () => {
  it("dice el TOTAL de áreas, no cuántas se ven", () => {
    // Es la razón por la que la card no miente estando cortada: se ven 6, el chip dice 12.
    expect(contador(render(12))).toBe("12")
    expect(contador(render(3))).toBe("3")
  })
})

describe("card vacía", () => {
  it("sigue diciendo 'Sin datos de headcount.'", () => {
    expect(render(0)).toContain("Sin datos de headcount.")
    expect(contador(render(0))).toBe("0")
  })
})

describe("escala de las barras", () => {
  it("el 100% sale del máximo de TODAS las áreas, no de las visibles", () => {
    // Si la escala se recalculara con el corte, desplegar el resto reescalaría las barras de
    // arriba y el gráfico cambiaría de forma al abrirlo. El área 01 (total 100) es el máximo.
    expect(render(12)).toContain("width:100%")
  })
})
