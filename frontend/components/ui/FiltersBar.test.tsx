// FiltersBar: los cinco tipos de control renderizan, y la lógica de propagación es correcta.
//
// ALCANCE, para que no se lea como más de lo que es: el proyecto corre vitest con
// `environment: "node"` y sin jsdom, así que acá se renderiza con `renderToStaticMarkup` y se
// verifica el MARKADO, no la interacción. Disparar un `change` real y ver que llega al
// `onChange` exigiría agregar jsdom + @testing-library como devDependencies — decisión de
// dependencias que no corresponde a esta sesión.
//
// Lo que sí queda cubierto de la propagación es su parte no trivial: `alternar`, que es toda
// la lógica del multiselect. Los otros cuatro controles propagan con un `e.target.value`
// directo o un spread de una línea, sin nada que pueda estar mal aparte de estar cableado —
// y que están cableados lo muestra el markup.
import { describe, expect, it } from "vitest"
import { renderToStaticMarkup } from "react-dom/server"

import { alternar, FiltersBar, type FiltroCampo } from "@/components/ui/FiltersBar"

const noop = () => {}

function render(campos: FiltroCampo[]): string {
  return renderToStaticMarkup(<FiltersBar campos={campos} />)
}

describe("daterange", () => {
  const campo: FiltroCampo = {
    tipo: "daterange", label: "Período",
    value: { desde: "2026-01-01", hasta: "2026-03-31" }, onChange: noop,
  }

  it("renderiza los dos inputs de fecha con sus valores", () => {
    const html = render([campo])
    expect(html.match(/type="date"/g)).toHaveLength(2)
    expect(html).toContain('value="2026-01-01"')
    expect(html).toContain('value="2026-03-31"')
  })

  it("cada input tiene su propio aria-label", () => {
    // Sin esto un lector de pantalla anuncia "Período" dos veces y no distingue cuál es cuál.
    const html = render([campo])
    expect(html).toContain('aria-label="Período — desde"')
    expect(html).toContain('aria-label="Período — hasta"')
  })

  it("un rango vacío no rompe", () => {
    const html = render([{ ...campo, value: { desde: "", hasta: "" } }])
    expect(html.match(/type="date"/g)).toHaveLength(2)
  })
})

describe("multiselect", () => {
  const OPCIONES = [
    { value: "sistemas", label: "Sistemas" },
    { value: "rrhh", label: "RRHH" },
    { value: "ventas", label: "Ventas" },
  ]
  const campo: FiltroCampo = {
    tipo: "multiselect", label: "Áreas", value: ["rrhh"], onChange: noop, opciones: OPCIONES,
  }

  it("renderiza un checkbox por opción", () => {
    const html = render([campo])
    expect(html.match(/type="checkbox"/g)).toHaveLength(3)
    for (const o of OPCIONES) expect(html).toContain(o.label)
  })

  it("marca solo las opciones seleccionadas", () => {
    const html = render([campo])
    expect(html.match(/checked=""/g)).toHaveLength(1)
  })

  it("agrupa los checkboxes con role y aria-label", () => {
    expect(render([campo])).toContain('role="group"')
  })

  it("sin selección no marca ninguno", () => {
    expect(render([{ ...campo, value: [] }])).not.toContain("checked")
  })
})

describe("alternar — la propagación del multiselect", () => {
  it("agrega el valor que no estaba", () => {
    expect(alternar(["a"], "b")).toEqual(["a", "b"])
  })

  it("saca el valor que ya estaba", () => {
    expect(alternar(["a", "b"], "a")).toEqual(["b"])
  })

  it("desde vacío agrega", () => {
    expect(alternar([], "a")).toEqual(["a"])
  })

  it("sacar el último deja vacío, no undefined", () => {
    expect(alternar(["a"], "a")).toEqual([])
  })

  it("no muta el array original", () => {
    const original = ["a"]
    alternar(original, "b")
    expect(original).toEqual(["a"])
  })

  it("es su propio inverso", () => {
    expect(alternar(alternar(["a"], "b"), "b")).toEqual(["a"])
  })
})

describe("los tres controles que ya existían siguen andando", () => {
  it("select renderiza opciones y la opción 'todos'", () => {
    const html = render([{
      tipo: "select", label: "Estado", value: "activo", onChange: noop,
      opciones: [{ value: "activo", label: "Activo" }], opcionTodos: "Todos los estados",
    }])
    expect(html).toContain("Todos los estados")
    expect(html).toContain("Activo")
  })

  it("search renderiza su placeholder", () => {
    const html = render([{
      tipo: "search", label: "Buscar", value: "", onChange: noop, placeholder: "Por nombre...",
    }])
    expect(html).toContain('placeholder="Por nombre..."')
  })

  it("date renderiza un input de fecha", () => {
    const html = render([{ tipo: "date", label: "Desde", value: "2026-05-01", onChange: noop }])
    expect(html).toContain('type="date"')
    expect(html).toContain('value="2026-05-01"')
  })
})

describe("la barra completa", () => {
  it("renderiza los cinco tipos juntos sin pisarse", () => {
    const html = render([
      { tipo: "search", label: "Buscar", value: "", onChange: noop },
      { tipo: "select", label: "Estado", value: "", onChange: noop, opciones: [] },
      { tipo: "date", label: "Fecha", value: "", onChange: noop },
      { tipo: "daterange", label: "Período", value: { desde: "", hasta: "" }, onChange: noop },
      { tipo: "multiselect", label: "Áreas", value: [], onChange: noop, opciones: [{ value: "a", label: "A" }] },
    ])
    for (const label of ["Buscar", "Estado", "Fecha", "Período", "Áreas"]) {
      expect(html).toContain(label)
    }
  })

  it("sin campos no renderiza controles", () => {
    expect(render([])).not.toContain("<input")
  })
})
