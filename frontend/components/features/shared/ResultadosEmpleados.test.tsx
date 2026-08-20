import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"

import { ResultadosEmpleados, mensajeVacio } from "@/components/features/shared/ResultadosEmpleados"
import type { Empleado } from "@/types/empleado"

/**
 * Lo que el selector de empleados MUESTRA en cada desenlace.
 *
 * 🚨 ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTOS TESTS PUEDAN FALLAR?
 *
 * **1. 🔴 LOS DOS VACÍOS SE AFIRMAN UNO CONTRA EL OTRO.** No alcanza con "muestra un mensaje":
 * el defecto que se está cerrando es exactamente que un vacío decía la frase del otro. Cada caso
 * afirma que aparece SU mensaje y que NO aparece el del hermano.
 *
 * **2. 🔴 EL ERROR SE PRUEBA CONTRA EL VACÍO, no contra la nada.** Un componente que pintara la
 * lista vacía en el camino de error pasaría cualquier test que solo mirara "no hay empleados en
 * el markup". Acá se exige el texto del error Y se prohíbe el del vacío.
 *
 * **3. 🔴 GUARDA DE MARKUP NO VACÍO.** Se renderiza a string porque vitest corre sin jsdom: si el
 * componente devolviera "" —porque revienta, porque cambia a `return null`— todas las aserciones
 * negativas pasarían sobre la nada. `_render` exige contenido antes de devolverlo.
 *
 * ⚠️ Lo que NO cubre: la interacción (escribir, elegir). Sin jsdom no hay eventos. Lo que se
 * pide al backend está cubierto en `buscarEmpleados.test.ts`, que es donde vive esa decisión.
 */

const BASE = {
  total: 0, cargando: false, error: false, termino: "",
  onElegir: () => {}, onReintentar: () => {},
}

const ALGUIEN = { id: "e1", nombre: "Ana", apellido: "Gómez", cargo: "Analista" } as Empleado

function _render(props: Partial<typeof BASE> & { empleados: Empleado[] }): string {
  const html = renderToStaticMarkup(<ResultadosEmpleados {...BASE} {...props} />)
  // 🔴 GUARDA: sin esto, un componente que devuelve "" pasa todas las aserciones negativas.
  expect(html.length).toBeGreaterThan(20)
  return html
}

describe("mensajeVacio distingue los dos vacíos", () => {
  it("🔴 'no hay nadie con ese nombre' NO es 'no hay empleados'", () => {
    const conBusqueda = mensajeVacio("Perez")
    const sinBusqueda = mensajeVacio("")

    expect(conBusqueda).not.toBe(sinBusqueda)
    expect(conBusqueda).toContain("Sin resultados")
    expect(conBusqueda).toContain("Perez")
    expect(sinBusqueda).toContain("No hay colaboradores")
    // El de búsqueda NO puede afirmar nada sobre la base: es la frase que ya mintió una vez.
    expect(conBusqueda).not.toContain("No hay colaboradores")
  })

  it("un término con espacios no genera un mensaje distinto al mismo término sin ellos", () => {
    expect(mensajeVacio("  Perez  ")).toBe(mensajeVacio("Perez"))
  })
})

describe("los cuatro desenlaces", () => {
  it("🔴 buscando algo que no está: 'sin resultados', NO 'no hay empleados'", () => {
    const html = _render({ empleados: [], termino: "Zzzz" })

    expect(html).toContain("Sin resultados")
    expect(html).not.toContain("No hay colaboradores")
  })

  it("🔴 sin buscar nada y sin nadie: ahí sí, 'no hay empleados activos'", () => {
    const html = _render({ empleados: [], termino: "" })

    expect(html).toContain("No hay colaboradores activos")
    expect(html).not.toContain("Sin resultados")
  })

  it("🔴 si el backend falló: error visible y reintento, NUNCA un vacío", () => {
    const html = _render({ empleados: [], termino: "Perez", error: true })

    expect(html).toContain("No se pudieron cargar")
    expect(html).toContain("Reintentar")
    expect(html).not.toContain("Sin resultados")
    expect(html).not.toContain("No hay colaboradores")
  })

  it("cargando no se confunde con vacío", () => {
    const html = _render({ empleados: [], termino: "Perez", cargando: true })

    expect(html).toContain("Buscando")
    expect(html).not.toContain("Sin resultados")
  })
})

describe("la lista dice cuánto está tapando", () => {
  it("🔴 con 400 del otro lado y 1 en pantalla, lo AVISA", () => {
    // El bug entero era éste: 100 de 400 se veía igual que 100 de 100.
    const html = _render({ empleados: [ALGUIEN], total: 400 })

    expect(html).toContain("Ana Gómez")
    expect(html).toContain("Mostrando 1 de 400")
  })

  it("🔴 y cuando NO tapa nada, no lo dice", () => {
    // El contraste: sin esto, el de arriba pasaría con un cartel incondicional que gritaría
    // "estás viendo una parte" sobre una empresa de tres personas.
    const html = _render({ empleados: [ALGUIEN], total: 1 })

    expect(html).toContain("Ana Gómez")
    expect(html).not.toContain("Mostrando")
  })
})
