import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { Pagination } from "@/components/ui/Pagination"

/**
 * Lo que la barra RENDERIZA. La aritmética está probada aparte, en `paginasVisibles.test.ts`;
 * acá sólo se verifica que salga a la pantalla lo que esa aritmética decidió, más el pie y el
 * selector. Se renderiza a string con react-dom/server porque el proyecto corre vitest SIN jsdom.
 *
 * ⚠️ Lo que este archivo NO puede probar, y no se disimula: los `onClick`. Sin jsdom no hay
 * eventos, así que "clickear la página 3 llama a onPageChange(3)" no es verificable acá. Lo que
 * sí se verifica es que cada número salga como un `<button>` propio y no como texto muerto, que
 * es la mitad del bug posible.
 */

const render = (props: Partial<Parameters<typeof Pagination>[0]> = {}) =>
  renderToStaticMarkup(
    <Pagination page={1} total={100} pageSize={10} onPageChange={vi.fn()} {...props} />,
  )

describe("Pagination — el pie", () => {
  it("dice qué rango se está viendo y sobre cuántas filas", () => {
    expect(render({ page: 1, total: 1042, pageSize: 12 })).toContain("Mostrando 1–12 de 1.042")
  })

  it("separa los miles como se lee en Argentina", () => {
    // 1042 y no 1,042: es el mismo criterio que el resto del front (Intl con "es-AR").
    expect(render({ page: 1, total: 1042, pageSize: 12 })).toContain("1.042")
  })

  it("la última página no dice más filas de las que hay", () => {
    expect(render({ page: 87, total: 1042, pageSize: 12 })).toContain("Mostrando 1.033–1.042")
  })

  it("sin resultados no muestra un rango dado vuelta", () => {
    const html = render({ total: 0 })
    expect(html).toContain("Sin resultados")
    expect(html).not.toContain("Mostrando")
  })
})

describe("Pagination — los números", () => {
  it("cada página visible sale como un botón clickeable, no como texto", () => {
    const html = render({ page: 40, total: 870, pageSize: 10 })
    for (const n of [1, 39, 40, 41, 87]) {
      expect(html).toContain(`aria-label="Página ${n}"`)
    }
  })

  it("la elipsis NO es un botón y se esconde del lector de pantalla", () => {
    const html = render({ page: 40, total: 870, pageSize: 10 })
    expect(html).toContain('aria-hidden="true"')
    expect(html).not.toContain('aria-label="Página …"')
  })

  it("la página actual se marca con aria-current", () => {
    const html = render({ page: 40, total: 870, pageSize: 10 })
    expect(html).toContain('aria-current="page"')
    // Una sola, no varias: dos `aria-current` dejarían al lector de pantalla sin saber dónde está.
    expect(html.match(/aria-current="page"/g)).toHaveLength(1)
  })

  it("la página actual sigue siendo clickeable (no disabled)", () => {
    // Deshabilitarla la saca del orden de tabulación y el foco salta al navegar con teclado.
    const html = render({ page: 3, total: 100, pageSize: 10 })
    const actual = html.slice(html.indexOf('aria-current="page"') - 400, html.indexOf('aria-current="page"'))
    expect(actual).not.toContain("disabled")
  })

  it("con una sola página no ofrece navegación falsa", () => {
    const html = render({ page: 1, total: 5, pageSize: 10 })
    expect(html).toContain('aria-label="Página 1"')
    expect(html).not.toContain('aria-label="Página 2"')
  })
})

describe("Pagination — los bordes", () => {
  it("en la primera página, Anterior está deshabilitado", () => {
    const html = render({ page: 1, total: 100, pageSize: 10 })
    const i = html.indexOf('aria-label="Página anterior"')
    expect(html.slice(Math.max(0, i - 300), i)).toContain("disabled")
  })

  it("en la última, Siguiente está deshabilitado", () => {
    const html = render({ page: 10, total: 100, pageSize: 10 })
    const i = html.indexOf('aria-label="Página siguiente"')
    expect(html.slice(Math.max(0, i - 300), i)).toContain("disabled")
  })
})

describe("Pagination — el selector de filas por página", () => {
  it("no aparece si el consumidor no lo habilita", () => {
    // Es lo que deja intactos a los 7 consumidores que pasan un PAGE_SIZE constante.
    expect(render()).not.toContain('aria-label="Filas por página"')
  })

  it("aparece cuando se pasa onPageSizeChange, con el valor actual seleccionado", () => {
    const html = render({ pageSize: 50, onPageSizeChange: vi.fn() })
    expect(html).toContain('aria-label="Filas por página"')
    expect(html).toContain('value="50"')
  })
})
