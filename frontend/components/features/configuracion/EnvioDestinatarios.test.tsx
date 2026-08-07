import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { EnvioDestinatarios } from "./EnvioDestinatarios"

/**
 * La lista de destinatarios: qué se ve marcado y qué no.
 *
 * Es la otra mitad de `envioAcciones.test.ts`. Aquel prueba que el body lleve los ids elegidos;
 * este prueba que la pantalla muestre marcados EXACTAMENTE esos y no otros. Los dos juntos son
 * lo que hace que "creí que le mandaba a dos" y "le mandé a dos" sean la misma cosa.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * 1. TRES empleados y DOS marcados. Con uno solo, un componente que marcara todas las casillas
 *    daría el mismo markup. Se cuentan las casillas marcadas, no se busca una: `toContain`
 *    sobre un `checked` pasaría con las tres marcadas.
 * 2. GUARDA DE MARKUP: cada render afirma primero que salió algo. Sin ella, un componente que no
 *    monte —o que quede dentro de un acordeón plegado o del portal de un Dialog, las dos cosas
 *    que devuelven "" en esta suite— haría pasar los tres casos con la misma salida vacía.
 * 3. Los ejes se recorren en los dos valores: lista con datos y lista vacía, con búsqueda y sin
 *    búsqueda, con email y sin email.
 *
 * ⚠️ LO QUE QUEDA SIN RED, explícito: el CLIC. vitest corre sin jsdom, así que no se puede
 * disparar el `onToggle`; lo que se prueba es qué muestra el componente dado un estado, no cómo
 * se llega a ese estado. La transición la cubre `useEnvioPlantilla`, que no tiene test.
 */

const EMPLEADOS = [
  { id: "e1", nombre: "Ana", apellido: "Uno", email_corporativo: "ana@k.com" },
  { id: "e2", nombre: "Beto", apellido: "Dos", email_corporativo: "beto@k.com" },
  { id: "e3", nombre: "Cari", apellido: "Tres", email_corporativo: "" },
]

function render(sel: string[], extra: Partial<{ search: string; cargando: boolean }> = {}): string {
  const html = renderToStaticMarkup(
    <EnvioDestinatarios
      visibles={EMPLEADOS} sel={new Set(sel)} search={extra.search ?? ""}
      cargando={extra.cargando ?? false} onSearch={() => {}} onToggle={() => {}}
    />,
  )
  expect(html.length, "la lista no renderizó nada: toda aserción de abajo sería vacua")
    .toBeGreaterThan(0)
  return html
}

/** Cuántas casillas quedaron marcadas. Se CUENTA: buscar "checked" pasaría con las tres. */
function marcadas(html: string): number {
  return [...html.matchAll(/<input[^>]*type="checkbox"[^>]*>/g)]
    .filter((m) => m[0].includes('checked=""')).length
}

function casillas(html: string): number {
  return [...html.matchAll(/<input[^>]*type="checkbox"[^>]*>/g)].length
}

describe("la selección que se ve es la que se manda", () => {
  it("🔴 con 3 en la lista y 2 elegidos, quedan 2 casillas marcadas de 3", () => {
    const html = render(["e1", "e3"])

    expect(casillas(html)).toBe(3)
    expect(marcadas(html)).toBe(2)
  })

  it("sin nadie elegido no hay ninguna marcada (si no, lo de arriba pasaría con todas marcadas)", () => {
    expect(marcadas(render([]))).toBe(0)
  })

  it("elegir a todos marca las tres", () => {
    expect(marcadas(render(["e1", "e2", "e3"]))).toBe(3)
  })

  it("los tres nombres se ven: nadie queda fuera de la vista por no estar seleccionado", () => {
    const html = render(["e1"])
    expect(html).toContain("Ana")
    expect(html).toContain("Beto")
    expect(html).toContain("Cari")
  })
})

describe("quién no tiene email se ve ANTES de mandar", () => {
  /** El backend lo cuenta como fallido con ese mismo motivo: verlo antes es la diferencia entre
   *  elegir a conciencia y enterarse en el resumen. */
  it("🔴 se marca, y no se lo esconde de la lista", () => {
    const html = render([])
    expect(html).toContain("sin email cargado")
    expect(html).toContain("Cari")
  })

  it("los que sí tienen muestran la dirección, no el aviso", () => {
    expect(render([])).toContain("ana@k.com")
  })
})

describe("estados vacíos", () => {
  function renderVacio(search: string): string {
    const html = renderToStaticMarkup(
      <EnvioDestinatarios
        visibles={[]} sel={new Set()} search={search} cargando={false}
        onSearch={() => {}} onToggle={() => {}}
      />,
    )
    expect(html.length).toBeGreaterThan(0)
    return html
  }

  it("sin búsqueda, el mensaje habla de que no hay empleados", () => {
    expect(renderVacio("")).toContain("No hay empleados activos")
  })

  it("con búsqueda, habla de la búsqueda — el motivo del vacío no es el mismo", () => {
    expect(renderVacio("zzz")).toContain("Nadie coincide con la búsqueda")
  })

  it("cargando no muestra 'no hay empleados': todavía no se sabe", () => {
    const html = renderToStaticMarkup(
      <EnvioDestinatarios
        visibles={[]} sel={new Set()} search="" cargando
        onSearch={() => {}} onToggle={() => {}}
      />,
    )
    expect(html).not.toContain("No hay empleados activos")
    expect(html).toContain("animate-pulse")
  })
})
