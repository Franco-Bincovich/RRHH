import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

import { FiltersBar } from "@/components/ui/FiltersBar"
import { FiltrosActivos } from "@/components/ui/FiltrosActivos"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import type { FiltroCampo } from "@/components/ui/filtrosTipos"

/**
 * La fila inferior del panel de filtros: los chips.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 * Los `onChange` de los campos son **spies de verdad**, no `noop`: cada aserción de "quitar el
 * chip X" mira lo que el campo recibió. Un `quitar` que no llamara a nada, o que llamara al campo
 * equivocado, rojea. Y el label legible se compara contra el texto de la OPCIÓN, no contra el
 * value: si `chipsDeCampos` volviera a mostrar el value crudo, "Preingreso" no aparece.
 *
 * ALCANCE: el proyecto corre vitest con `environment: "node"` y sin jsdom, así que el render es a
 * string (`renderToStaticMarkup`) y los handlers se invocan a mano — no hay clicks. Es la misma
 * limitación declarada en `FiltersBar.test.tsx` y en `Pagination.test.tsx`.
 */

const ESTADOS = [
  { value: "activo", label: "Activo" },
  { value: "preingreso", label: "Preingreso" },
]

function campos(over: { estado?: string; search?: string; onEstado?: (v: string) => void; onSearch?: (v: string) => void } = {}): FiltroCampo[] {
  return [
    { tipo: "search", label: "Buscar", value: over.search ?? "", onChange: over.onSearch ?? (() => {}) },
    { tipo: "select", label: "Estado", value: over.estado ?? "", opciones: ESTADOS, onChange: over.onEstado ?? (() => {}) },
  ]
}

describe("el chip muestra el label legible, no el value", () => {
  it("'preingreso' se muestra como 'Estado: Preingreso'", () => {
    const [chip] = chipsDeCampos(campos({ estado: "preingreso" }))
    expect(chip.etiqueta).toBe("Estado")
    expect(chip.valor).toBe("Preingreso")
  })

  it("un value que todavía no está en las opciones se muestra crudo, no se esconde", () => {
    // Los catálogos (áreas, proyectos) llegan por fetch y el filtro puede venir sembrado desde la
    // querystring antes que ellos. Un filtro activo invisible es la pantalla mostrando 4 filas de
    // 31 sin decir por qué.
    const [chip] = chipsDeCampos([
      { tipo: "select", label: "Área", value: "uuid-sistemas", opciones: [], onChange: () => {} },
    ])
    expect(chip.valor).toBe("uuid-sistemas")
  })

  it("la fecha se muestra como la escribió el usuario, no en ISO", () => {
    const [chip] = chipsDeCampos([{ tipo: "date", label: "Ingreso", value: "2026-03-25", onChange: () => {} }])
    expect(chip.valor).toBe("25/03/2026")
  })

  it("un rango abierto se lee como rango abierto", () => {
    const armar = (desde: string, hasta: string): FiltroCampo[] => [
      { tipo: "daterange", label: "Período", value: { desde, hasta }, onChange: () => {} },
    ]
    expect(chipsDeCampos(armar("2026-03-01", "2026-03-31"))[0].valor).toBe("01/03/2026 – 31/03/2026")
    expect(chipsDeCampos(armar("2026-03-01", ""))[0].valor).toBe("desde 01/03/2026")
    expect(chipsDeCampos(armar("", "2026-03-31"))[0].valor).toBe("hasta 31/03/2026")
  })

  it("el multiselect junta sus valores en UN chip", () => {
    const [chip] = chipsDeCampos([{
      tipo: "multiselect", label: "Estados", value: ["activo", "preingreso"], opciones: ESTADOS, onChange: () => {},
    }])
    expect(chip.valor).toBe("Activo, Preingreso")
  })
})

describe("(a) con dos filtros activos aparecen dos chips", () => {
  const html = renderToStaticMarkup(
    <FiltrosActivos chips={chipsDeCampos(campos({ estado: "preingreso", search: "juan" }))} />,
  )

  it("uno por filtro, con su label legible", () => {
    expect(html).toContain("Estado")
    expect(html).toContain("Preingreso")
    expect(html).toContain("Buscar")
    expect(html).toContain("juan")
  })

  it("el contador dice cuántos son", () => {
    expect(html).toContain("2 filtros activos")
  })

  it("cada chip trae su ✕ con un nombre que dice cuál quita", () => {
    expect(html).toContain('aria-label="Quitar filtro Estado"')
    expect(html).toContain('aria-label="Quitar filtro Buscar"')
  })

  it("con uno solo el contador va en singular", () => {
    const uno = renderToStaticMarkup(<FiltrosActivos chips={chipsDeCampos(campos({ estado: "activo" }))} />)
    expect(uno).toContain("1 filtro activo")
    expect(uno).not.toContain("1 filtros")
  })
})

describe("(b) quitar un chip quita ESE filtro y no los otros", () => {
  it("el chip llama al onChange de su propio campo, con el valor vacío", () => {
    const onEstado = vi.fn()
    const onSearch = vi.fn()
    const chips = chipsDeCampos(campos({ estado: "preingreso", search: "juan", onEstado, onSearch }))

    chips.find((c) => c.clave === "Estado")!.quitar()

    expect(onEstado).toHaveBeenCalledWith("")
    expect(onSearch).not.toHaveBeenCalled()
  })

  it("cada tipo se limpia con el vacío que su control entiende", () => {
    // Un multiselect limpiado con "" en vez de [] deja el filtro puesto y el chip ahí para siempre.
    const onMulti = vi.fn()
    const onRango = vi.fn()
    chipsDeCampos([
      { tipo: "multiselect", label: "Estados", value: ["activo"], opciones: ESTADOS, onChange: onMulti },
      { tipo: "daterange", label: "Período", value: { desde: "2026-03-01", hasta: "" }, onChange: onRango },
    ]).forEach((c) => c.quitar())

    expect(onMulti).toHaveBeenCalledWith([])
    expect(onRango).toHaveBeenCalledWith({ desde: "", hasta: "" })
  })
})

describe("(d) 'Limpiar todo' deja cero chips", () => {
  it("llama al onChange de todos los campos activos", () => {
    const onEstado = vi.fn()
    const onSearch = vi.fn()
    const chips = chipsDeCampos(campos({ estado: "preingreso", search: "juan", onEstado, onSearch }))

    // Es lo que hace el botón: cada chip quitándose a sí mismo.
    chips.forEach((c) => c.quitar())

    expect(onEstado).toHaveBeenCalledWith("")
    expect(onSearch).toHaveBeenCalledWith("")
    // Y con los campos ya limpios no queda ningún chip: la fila desaparece.
    expect(chipsDeCampos(campos())).toEqual([])
    expect(renderToStaticMarkup(<FiltrosActivos chips={chipsDeCampos(campos())} />)).toBe("")
  })
})

describe("(e) sin filtros activos la fila inferior no se renderiza", () => {
  it("FiltrosActivos devuelve null, no una fila vacía", () => {
    expect(renderToStaticMarkup(<FiltrosActivos chips={[]} />)).toBe("")
  })

  it("el panel no muestra el contador ni 'Limpiar todo'", () => {
    const html = renderToStaticMarkup(<FiltersBar campos={campos()} panel />)
    expect(html).not.toContain("filtros activos")
    expect(html).not.toContain("Limpiar todo")
    // Contracara: con un filtro puesto sí están. Sin esto, un panel que no renderizara nunca los
    // chips pasaría este bloque entero.
    const conFiltro = renderToStaticMarkup(<FiltersBar campos={campos({ estado: "activo" })} panel />)
    expect(conFiltro).toContain("1 filtro activo")
    expect(conFiltro).toContain("Limpiar todo")
  })

  it("un espacio en el buscador no es un filtro activo", () => {
    expect(chipsDeCampos(campos({ search: "   " }))).toEqual([])
  })
})

describe("el panel es OPT-IN: sin él la barra queda como estaba", () => {
  it("sin `panel` no hay chips ni 'Más filtros', aunque haya filtros puestos", () => {
    // Es lo que protege a las otras 7 pantallas que ya usaban FiltersBar: la migración es de a una.
    const html = renderToStaticMarkup(<FiltersBar campos={campos({ estado: "activo" })} />)
    expect(html).not.toContain("filtro activo")
    expect(html).not.toContain("Más filtros")
  })

  it("con `panel`, los campos `avanzado` salen de la fila superior y quedan atrás del botón", () => {
    const conAvanzado: FiltroCampo[] = [
      ...campos(),
      { tipo: "select", label: "Proyecto", value: "", opciones: [], onChange: () => {}, avanzado: true },
    ]
    const html = renderToStaticMarkup(<FiltersBar campos={conAvanzado} panel />)
    expect(html).toContain("Más filtros")
    expect(html).not.toContain("Proyecto")
  })

  it("si un filtro avanzado viene puesto, el panel arranca ABIERTO", () => {
    // El caso real: la alerta del dashboard linkea a /empleados?sin_manager=true, y "Superior" es
    // avanzado. Con el panel cerrado, el control que recorta el listado queda atrás de un botón.
    const conAvanzado: FiltroCampo[] = [
      ...campos(),
      { tipo: "select", label: "Proyecto", value: "p1", opciones: [{ value: "p1", label: "Karstec" }], onChange: () => {}, avanzado: true },
    ]
    expect(renderToStaticMarkup(<FiltersBar campos={conAvanzado} panel />)).toContain("Proyecto")
  })
})
