import { describe, expect, it } from "vitest"

import { ELIPSIS, paginasVisibles, rangoVisible } from "@/components/ui/paginasVisibles"

/**
 * La aritmética de la barra de paginación.
 *
 * Se prueba la FUNCIÓN y no el componente a propósito: `vitest` corre sin jsdom, así que un test
 * de `Pagination` verificaría el markup —que existan los `<button>`— y no la regla que decide qué
 * números entran. Acá la regla es todo lo que hay, y se puede desmentir con un caso.
 */

describe("paginasVisibles", () => {
  it("con una sola página devuelve solo la 1", () => {
    expect(paginasVisibles(1, 1)).toEqual([1])
  })

  it("con total 0 no explota ni inventa páginas", () => {
    // `totalPages` nunca llega en 0 desde el componente (usa Math.max(1, ...)), pero la función
    // es pública y un 0 no puede devolver una barra vacía.
    expect(paginasVisibles(1, 0)).toEqual([1])
  })

  it("hasta 7 páginas las muestra todas, sin elipsis", () => {
    expect(paginasVisibles(4, 7)).toEqual([1, 2, 3, 4, 5, 6, 7])
  })

  it("al principio de una lista larga elide solo del lado derecho", () => {
    expect(paginasVisibles(1, 87)).toEqual([1, 2, ELIPSIS, 87])
  })

  it("al final elide solo del lado izquierdo", () => {
    expect(paginasVisibles(87, 87)).toEqual([1, ELIPSIS, 86, 87])
  })

  it("en el medio elide de los dos lados", () => {
    expect(paginasVisibles(40, 87)).toEqual([1, ELIPSIS, 39, 40, 41, ELIPSIS, 87])
  })

  it("🔑 un hueco de UNA sola página se imprime como el número, no como elipsis", () => {
    // Es el bug clásico de esta función: entre 1 y 3 falta solo la 2, y una elipsis ahí ocupa lo
    // mismo que el número pero esconde una página clickeable.
    expect(paginasVisibles(3, 9)).toEqual([1, 2, 3, 4, ELIPSIS, 9])
    expect(paginasVisibles(7, 9)).toEqual([1, ELIPSIS, 6, 7, 8, 9])
  })

  it("nunca repite un número", () => {
    for (let total = 1; total <= 40; total++) {
      for (let page = 1; page <= total; page++) {
        const nums = paginasVisibles(page, total).filter((x) => x !== ELIPSIS)
        expect(new Set(nums).size).toBe(nums.length)
      }
    }
  })

  it("siempre incluye la página actual, la primera y la última", () => {
    for (let total = 1; total <= 40; total++) {
      for (let page = 1; page <= total; page++) {
        const items = paginasVisibles(page, total)
        expect(items).toContain(page)
        expect(items).toContain(1)
        expect(items).toContain(total)
      }
    }
  })

  it("los números salen en orden creciente", () => {
    const nums = paginasVisibles(40, 87).filter((x): x is number => x !== ELIPSIS)
    expect([...nums].sort((a, b) => a - b)).toEqual(nums)
  })

  it("el ancho está ACOTADO: la barra no crece con el total", () => {
    // La propiedad real es una cota (2*vecinos + 5 = 7), no un ancho constante: cerca de los
    // bordes la regla del hueco-de-una-página cambia una elipsis por un número y da 6. Afirmar
    // "siempre 7" sería más fuerte de lo que la función promete — y falso.
    const anchos = new Set<number>()
    for (let total = 1; total <= 200; total++) {
      for (let page = 1; page <= total; page++) anchos.add(paginasVisibles(page, total).length)
    }
    expect(Math.max(...anchos)).toBe(7)
  })

  it("una página fuera de rango se acota en vez de devolver una ventana rota", () => {
    // Pasa de verdad: al aplicar un filtro el total baja y `page` queda más allá del final.
    expect(paginasVisibles(99, 5)).toEqual(paginasVisibles(5, 5))
    expect(paginasVisibles(0, 5)).toEqual(paginasVisibles(1, 5))
  })
})

describe("rangoVisible", () => {
  it("la primera página arranca en 1", () => {
    expect(rangoVisible(1, 12, 1042)).toEqual([1, 12])
  })

  it("la segunda sigue donde terminó la primera", () => {
    expect(rangoVisible(2, 12, 1042)).toEqual([13, 24])
  })

  it("🔑 la última página no miente: se acota con el total", () => {
    // Sin el `min`, diría "Mostrando 1.033–1.044 de 1.042".
    expect(rangoVisible(87, 12, 1042)).toEqual([1033, 1042])
  })

  it("sin resultados devuelve [0, 0] y no un rango dado vuelta", () => {
    expect(rangoVisible(1, 12, 0)).toEqual([0, 0])
  })

  it("una página más allá del final devuelve [0, 0]", () => {
    expect(rangoVisible(50, 12, 10)).toEqual([0, 0])
  })

  it("el rango cubre exactamente pageSize salvo en la última", () => {
    const [d1, h1] = rangoVisible(1, 20, 45)
    const [d3, h3] = rangoVisible(3, 20, 45)
    expect(h1 - d1 + 1).toBe(20)
    expect(h3 - d3 + 1).toBe(5)
  })
})
