/**
 * El selector de filas por página: qué hace al cambiarlo.
 *
 * 🔴 LA INVARIANTE QUE SE PRUEBA ACÁ NO ESTABA EN NINGÚN LADO. Hasta el 25/8/2026 el reseteo a la
 * página 1 lo hacía cada consumidor (`{ setPageSize(n); setPage(1) }`), y eran 4. Al cablear los
 * 17 que paginan, una regla que cada uno copia es una regla que alguno olvida — y el síntoma es
 * feo y mudo: pasar de 100 a 20 filas estando en la página 9 pide una página que ya no existe, o
 * sea una tabla vacía sobre un filtro con datos. Ahora la hace el primitivo, y esto la fija.
 *
 * ⚠️ ¿QUÉ TENDRÍA QUE SER DISTINTO PARA QUE ESTE TEST PUEDA FALLAR? Se dispara el `onChange` REAL
 * del `<select>` sobre el markup renderizado y se miran los DOS callbacks. Afirmar sólo que
 * `onPageSizeChange` se llamó pasaría con el reseteo borrado, que es justamente lo que se agregó.
 */
import { describe, expect, it, vi } from "vitest"

import { Pagination } from "@/components/ui/Pagination"

/** Ejecuta el `onChange` del selector sin jsdom: se lo saca del árbol de React directamente. */
function cambiarTamano(a: number): { size: number[]; pages: number[] } {
  const size: number[] = []
  const pages: number[] = []
  const el = Pagination({
    page: 9, total: 1000, pageSize: 100,
    onPageChange: (p) => pages.push(p),
    onPageSizeChange: (n) => size.push(n),
  }) as { props: { children: unknown } }

  // El `<select>` es el único control con `aria-label="Filas por página"`.
  const buscar = (nodo: unknown): { props: Record<string, unknown> } | null => {
    if (!nodo || typeof nodo !== "object") return null
    const n = nodo as { props?: Record<string, unknown> }
    if (n.props?.["aria-label"] === "Filas por página") return n as never
    const hijos = n.props?.children
    for (const h of Array.isArray(hijos) ? hijos : [hijos]) {
      const r = buscar(h)
      if (r) return r
    }
    return null
  }
  const select = buscar(el)
  if (!select) throw new Error("no se encontró el selector de filas por página")
  ;(select.props.onChange as (e: unknown) => void)({ target: { value: String(a) } })
  return { size, pages }
}

describe("cambiar el tamaño de página", () => {
  it("avisa el tamaño nuevo Y vuelve a la página 1", () => {
    const { size, pages } = cambiarTamano(20)
    expect(size).toEqual([20])
    // Sin esto, la página 9 de 100 filas no existe con 20 y la tabla sale vacía.
    expect(pages).toEqual([1])
  })
})
