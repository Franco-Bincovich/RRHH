import { readFileSync } from "node:fs"
import path from "node:path"

import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { chipsDeCampos } from "@/components/ui/filtrosChips"
import type { ChipFiltro } from "@/components/ui/filtrosChips"

import { construirCampos, type ArgsCamposCandidatos } from "./_camposCandidatos"
import { CandidatosLista } from "./CandidatosLista"

/**
 * Los cuatro puntos del patrón del bloque B sobre /candidatos, con la vuelta propia de esta
 * pantalla: **no es una tabla, son tarjetas por búsqueda**, así que (c) no puede verificar un
 * `<thead>` que no existe. Lo que sí se verifica es lo que el patrón deja igual: el TEXTO del
 * vacío sale de `textoVacio()` con los mismos chips, y las dos salidas se ofrecen sin ejecutarse.
 *
 * 🔴 (a) y (b) VAN CONTRA `construirCampos`, EL CABLEADO REAL. Con campos inventados el chip
 * llamaría a un `onChange` de mentira y el test pasaría con el cableado roto.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTO PUEDA FALLAR?
 *   · (a) que "Sin búsqueda asignada" volviera a ser un checkbox: no produce chip, y la pantalla
 *     muestra 4 de 31 candidatos sin decir por qué.
 *   · (b) que un `onChange` se olvidara de `onFiltroChange`.
 *   · (c) que el vacío volviera al literal "Todavía no hay candidatos cargados" con filtros
 *     puestos: es verdadero y no dice cuál de los dos filtros dejó la pantalla en cero.
 *   · (d) que la página le pasara `candidatos.length` a `<Pagination>`.
 */

function args(over: Partial<ArgsCamposCandidatos> = {}): ArgsCamposCandidatos {
  return {
    asignacionFiltro: "", setAsignacionFiltro: vi.fn(),
    clasificacion: "", setClasificacion: vi.fn(),
    onFiltroChange: vi.fn(),
    ...over,
  }
}

describe("(a) los chips muestran el label legible, no el value crudo", () => {
  it("la clasificación dice 'No relevante' y no 'no_relevante'", () => {
    const chips = chipsDeCampos(construirCampos(args({ clasificacion: "no_relevante" })))
    expect(chips.find((c) => c.clave === "Clasificación")!.valor).toBe("No relevante")
  })

  it("y 'Sin clasificar' es un VALOR con chip, no la ausencia de filtro", () => {
    // Es la distinción que el backend también hace (`Clasificacion` incluye `sin_clasificar`):
    // sin chip, el usuario no puede distinguir "filtré por sin clasificar" de "no filtré".
    const chips = chipsDeCampos(construirCampos(args({ clasificacion: "sin_clasificar" })))
    expect(chips.find((c) => c.clave === "Clasificación")!.valor).toBe("Sin clasificar")
  })

  it("🔴 'Sin búsqueda asignada' PRODUCE CHIP — el checkbox de antes no producía ninguno", () => {
    const chips = chipsDeCampos(construirCampos(args({ asignacionFiltro: "sin" })))
    expect(chips.find((c) => c.clave === "Asignación")!.valor).toBe("Sin búsqueda asignada")
  })

  it("sin filtros no hay ningún chip, así que tampoco hay contador que mostrar", () => {
    // Contracara: sin esto, un `chipsDeCampos` que devolviera siempre dos chips pasaría todo lo
    // de arriba y la fila inferior aparecería con la pantalla sin filtrar.
    expect(chipsDeCampos(construirCampos(args()))).toEqual([])
  })
})

describe("(b) quitar un chip quita ESE filtro, no los otros, y resetea a página 1", () => {
  it("quitar Clasificación no toca Asignación", () => {
    const a = args({ clasificacion: "relevante", asignacionFiltro: "sin" })
    chipsDeCampos(construirCampos(a)).find((c) => c.clave === "Clasificación")!.quitar()

    expect(a.setClasificacion).toHaveBeenCalledWith("")
    expect(a.onFiltroChange).toHaveBeenCalled()
    expect(a.setAsignacionFiltro).not.toHaveBeenCalled()
  })

  it("vale para los dos filtros, no sólo para Clasificación", () => {
    const a = args({ clasificacion: "relevante", asignacionFiltro: "sin" })
    const chips = chipsDeCampos(construirCampos(a))
    // Guarda contra el falso verde: sin chips, el for de abajo no compara nada.
    expect(chips.length).toBe(2)

    for (const chip of chips) {
      const antes = (a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length
      chip.quitar()
      expect((a.onFiltroChange as ReturnType<typeof vi.fn>).mock.calls.length, `el chip "${chip.etiqueta}" no reseteó la página`).toBe(antes + 1)
    }
  })

  it("ninguno de los dos filtros es avanzado: con dos, esconder uno no compra nada", () => {
    expect(construirCampos(args()).filter((c) => c.avanzado)).toEqual([])
  })
})

const chip = (etiqueta: string, valor: string, quitar = () => {}): ChipFiltro => ({ clave: etiqueta, etiqueta, valor, quitar })

function lista(props: Partial<Parameters<typeof CandidatosLista>[0]> = {}) {
  return renderToStaticMarkup(
    <CandidatosLista
      grupos={[]} loading={false} error={false}
      chips={[chip("Clasificación", "Relevante")]}
      onRetry={() => {}} onSelect={() => {}} onLimpiarTodo={() => {}}
      {...props}
    />,
  )
}

describe("(c) el vacío con filtros activos usa los valores reales", () => {
  it("la frase arranca IMPERSONAL: en esta pantalla la empresa no es un filtro", () => {
    // El sujeto del texto vacío es siempre la empresa, y acá llega por el selector del sidebar
    // (header del request), no por un control del panel. Sin sujeto, la frase es "No hay…".
    expect(lista()).toContain("No hay candidatos con clasificación Relevante.")
  })

  it("ofrece quitar el ÚLTIMO chip y limpiar todo, sin ejecutar ninguna de las dos", () => {
    const html = lista({ chips: [chip("Asignación", "Sin búsqueda asignada"), chip("Clasificación", "Dudoso")] })
    expect(html).toContain("Quitar clasificación: Dudoso")
    expect(html).not.toContain("Quitar asignación")
    expect(html).toContain("Limpiar todo")
  })

  it("sin filtros es la otra pantalla: 'todavía no hay', y sin nada que quitar", () => {
    const html = lista({ chips: [] })
    expect(html).toContain("Todavía no hay candidatos")
    expect(html).not.toContain("Limpiar todo")
  })

  it("durante la carga el esqueleto son tarjetas del mismo alto, con shimmer", () => {
    const html = lista({ loading: true })
    expect(html).toContain("animate-shimmer")
    expect(html).toContain("h-40")
  })
})

const PAGINA = path.resolve(__dirname, "..", "..", "..", "app", "(dashboard)", "candidatos", "page.tsx")

/** El código sin comentarios. `\r\n` normalizado ANTES de nada: con finales de Windows cada línea
 *  termina en `\r`, que para el regex de JS es un terminador, así que `//.*$` no matchea nunca. */
function sinComentarios(src: string): string {
  return src.replace(/\r\n/g, "\n").replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n").map((l) => l.replace(/\/\/.*$/, "")).join("\n")
}

describe("(d) el contador del pie sale de `total`, nunca de candidatos.length", () => {
  it("la página le pasa `total={total}` a <Pagination>", () => {
    const jsx = readFileSync(PAGINA, "utf8").match(/<Pagination[\s\S]*?\/>/)
    expect(jsx, "la página dejó de renderizar <Pagination>").not.toBeNull()
    expect(jsx![0]).toContain("total={total}")
    expect(/total=\{[^}]*\.length[^}]*\}/.test(jsx![0])).toBe(false)
  })

  it("🔴 el pie va SIEMPRE que haya filas, no sólo con más de una página", () => {
    const codigo = sinComentarios(readFileSync(PAGINA, "utf8"))
    expect(codigo).toContain("candidatos.length > 0 && (")
    expect(codigo).not.toContain("total > PAGE_SIZE")
    // Contracara: sin esto, un `sinComentarios` que devolviera "" pasaría las dos de arriba.
    expect(sinComentarios("if (total > PAGE_SIZE) {}")).toContain("total > PAGE_SIZE")
  })
})
