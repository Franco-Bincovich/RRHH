import { beforeEach, describe, expect, it, vi } from "vitest"

const { fetchRecategorizaciones } = vi.hoisted(() => ({ fetchRecategorizaciones: vi.fn() }))
vi.mock("@/services/recategorizaciones", () => ({ fetchRecategorizaciones }))

import type { Recategorizacion } from "@/types/recategorizacion"

import { cargarRecategorizaciones } from "./cargarRecategorizaciones"

/**
 * (g) el contador sale de `total`, no de `items.length`.
 *
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * 🔴 QUÉ TENDRÍA QUE SER DISTINTO PARA QUE (g) PUEDA FALLAR
 * ═════════════════════════════════════════════════════════════════════════════════════════
 * La respuesta del fake trae **3 items y un total de 340**. Con un fake donde los dos números
 * coincidieran —lo natural de escribir— `setTotal(items.length)` pasaría en verde, y el bug
 * quedaría vivo: el encabezado diría "20 recategorizaciones" habiendo 340 y el paginador
 * calcularía UNA sola página, escondiendo las otras 16 sin ningún error a la vista.
 *
 * Es la misma clase de bug que `HorasTab` ya pagó una vez (decía "9 h" con 400 h cargadas, porque
 * sumaba con `.reduce()` sobre la página en lugar de leer el total del backend), y por eso el
 * caso que se prueba es justamente aquel en el que los dos números NO son iguales.
 */

const fila = (id: string): Recategorizacion => ({ id } as Recategorizacion)

function estado() {
  return { setItems: vi.fn(), setTotal: vi.fn(), setLoading: vi.fn(), setError: vi.fn() }
}

beforeEach(() => {
  fetchRecategorizaciones.mockReset().mockResolvedValue({
    items: [fila("a"), fila("b"), fila("c")], total: 340, page: 1, page_size: 20, total_pages: 17,
  })
})

describe("(g) el total viene del backend, no de la página", () => {
  it("🔴 con 3 items y total 340, el contador dice 340", async () => {
    const e = estado()
    await cargarRecategorizaciones({}, 1, 20, e)
    expect(e.setTotal).toHaveBeenCalledWith(340)
    expect(e.setTotal).not.toHaveBeenCalledWith(3)
  })

  it("y los items son los de la página, sin tocar", async () => {
    const e = estado()
    await cargarRecategorizaciones({}, 1, 20, e)
    expect(e.setItems).toHaveBeenCalledWith([fila("a"), fila("b"), fila("c")])
  })

  it("una respuesta sin `total` cae a 0, no al largo de la lista", async () => {
    // `?? 0` y no `?? items.length`: si el backend dejara de mandar el conteo, decir "3" sería
    // afirmar un número inventado; decir 0 es visiblemente raro y se investiga.
    fetchRecategorizaciones.mockResolvedValue({ items: [fila("a")] })
    const e = estado()
    await cargarRecategorizaciones({}, 1, 20, e)
    expect(e.setTotal).toHaveBeenCalledWith(0)
  })
})

describe("los tres desenlaces de la carga", () => {
  it("el loading se apaga SIEMPRE en el camino de éxito", async () => {
    const e = estado()
    await cargarRecategorizaciones({}, 1, 20, e)
    expect(e.setLoading).toHaveBeenNthCalledWith(1, true)
    expect(e.setLoading).toHaveBeenLastCalledWith(false)
    expect(e.setError).toHaveBeenCalledWith(false)
  })

  it("🔴 y TAMBIÉN en el de error, que es el que se pierde al dividir un componente", async () => {
    // Apagarlo dentro del `try` deja la pantalla cargando encima del mensaje que el `catch`
    // acaba de escribir. Es la regresión que se llevó puesta la pantalla de proyectos.
    fetchRecategorizaciones.mockRejectedValue(new Error("red caída"))
    const e = estado()
    await cargarRecategorizaciones({}, 1, 20, e)
    expect(e.setError).toHaveBeenLastCalledWith(true)
    expect(e.setLoading).toHaveBeenLastCalledWith(false)
  })

  it("un error NO se confunde con una lista vacía: no toca los items", async () => {
    fetchRecategorizaciones.mockRejectedValue(new Error("red caída"))
    const e = estado()
    await cargarRecategorizaciones({}, 1, 20, e)
    expect(e.setItems).not.toHaveBeenCalled()
  })

  it("un 200 sin items no revienta: la lista queda vacía de verdad", async () => {
    fetchRecategorizaciones.mockResolvedValue({ total: 0 })
    const e = estado()
    await cargarRecategorizaciones({}, 1, 20, e)
    expect(e.setItems).toHaveBeenCalledWith([])
    expect(e.setError).not.toHaveBeenCalledWith(true)
  })
})
