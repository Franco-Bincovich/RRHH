// El helper del molde de filtros: normalización de "vacío" a `undefined`.
//
// Es la pieza que hace que un control vacío NO viaje al backend como filtro real. Cuando
// falla, el síntoma es una pantalla que se ve bien y sale vacía: se manda `estado=""`, el
// repo hace `.eq("estado", "")` y no matchea nada. Cuesta rastrearlo justamente porque no
// hay error.
import { describe, expect, it } from "vitest"

import { filtrosActivos, setFiltro } from "@/components/features/shared/filtros"

type Filtros = { estado?: string; areas?: string[]; search?: string }

/** Aplica un set y devuelve el objeto resultante. */
function aplicar(inicial: Filtros, campo: keyof Filtros, valor: Filtros[keyof Filtros]): Filtros {
  let resultado: Filtros = inicial
  setFiltro(inicial, (f) => { resultado = f })(campo, valor as never)
  return resultado
}

describe("setFiltro", () => {
  it("guarda un valor con contenido", () => {
    expect(aplicar({}, "estado", "activo")).toEqual({ estado: "activo" })
  })

  it("normaliza el string vacío a undefined", () => {
    expect(aplicar({ estado: "activo" }, "estado", "")).toEqual({ estado: undefined })
  })

  it("normaliza el array vacío a undefined", () => {
    // multiselect sin nada tildado = sin filtro, no "filtrar por ninguna área"
    expect(aplicar({ areas: ["a"] }, "areas", [])).toEqual({ areas: undefined })
  })

  it("guarda un array con contenido", () => {
    expect(aplicar({}, "areas", ["a", "b"])).toEqual({ areas: ["a", "b"] })
  })

  it("normaliza undefined a undefined", () => {
    expect(aplicar({ estado: "activo" }, "estado", undefined)).toEqual({ estado: undefined })
  })

  it("no toca los otros campos", () => {
    expect(aplicar({ estado: "activo", search: "ana" }, "estado", "baja"))
      .toEqual({ estado: "baja", search: "ana" })
  })

  it("no muta el objeto original", () => {
    const original: Filtros = { estado: "activo" }
    aplicar(original, "estado", "baja")
    expect(original).toEqual({ estado: "activo" })
  })
})

describe("filtrosActivos", () => {
  it("saca los undefined", () => {
    expect(filtrosActivos({ estado: "activo", search: undefined })).toEqual({ estado: "activo" })
  })

  it("saca los strings vacíos", () => {
    expect(filtrosActivos({ estado: "", search: "ana" })).toEqual({ search: "ana" })
  })

  it("saca los arrays vacíos", () => {
    expect(filtrosActivos({ areas: [], estado: "activo" })).toEqual({ estado: "activo" })
  })

  it("conserva los arrays con contenido", () => {
    expect(filtrosActivos({ areas: ["a"] })).toEqual({ areas: ["a"] })
  })

  it("todo vacío da objeto vacío", () => {
    expect(filtrosActivos({ estado: "", areas: [], search: undefined })).toEqual({})
  })
})
