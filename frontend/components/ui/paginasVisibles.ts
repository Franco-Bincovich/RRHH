/**
 * La ventana de números que muestra la paginación: `1 … 5 6 7 … 87`.
 *
 * ARCHIVO PROPIO Y FUNCIÓN PURA a propósito. `vitest` corre con `environment: "node"` y sin
 * jsdom: los tests de componentes usan `renderToStaticMarkup` y verifican MARKUP, que para esto
 * probaría el `<button>` y no la regla. Acá la regla es aritmética —qué números entran y dónde
 * va la elipsis— así que se prueba directo, con casos, sin renderizar nada.
 */

/** El carácter de la elipsis. Exportado para que los tests no lo re-escriban a mano. */
export const ELIPSIS = "…" as const

export type ItemPaginacion = number | typeof ELIPSIS

/**
 * Los números a mostrar para `page` dentro de `totalPages`, con elipsis en los huecos.
 *
 * Siempre entran la primera y la última página (son los saltos que más se usan) más `vecinos`
 * páginas a cada lado de la actual. El ancho de la salida es estable —nunca más de
 * `2*vecinos + 5` elementos— así que la barra no cambia de tamaño al navegar, que es lo que hace
 * que los números no se muevan bajo el mouse.
 *
 * 🔑 UN HUECO DE UNA SOLA PÁGINA SE IMPRIME COMO EL NÚMERO, NO COMO "…". Es el bug clásico de
 * esta función: entre 1 y 3 falta sólo la 2, y una elipsis ahí ocupa lo mismo que el número pero
 * esconde una página que se podía clickear. Es el caso `gap === 2` de abajo.
 */
export function paginasVisibles(
  page: number,
  totalPages: number,
  vecinos = 1,
): ItemPaginacion[] {
  if (totalPages <= 1) return [1]
  // `page` fuera de rango no es hipotético: al filtrar, el total baja y la página actual puede
  // quedar más allá del final por un render. Se acota en vez de devolver una ventana vacía.
  const actual = Math.min(Math.max(Math.trunc(page), 1), totalPages)

  const claves = new Set<number>([1, totalPages])
  for (let i = actual - vecinos; i <= actual + vecinos; i++) {
    if (i >= 1 && i <= totalPages) claves.add(i)
  }

  const ordenadas = [...claves].sort((a, b) => a - b)
  const salida: ItemPaginacion[] = []
  for (let i = 0; i < ordenadas.length; i++) {
    if (i > 0) {
      const hueco = ordenadas[i] - ordenadas[i - 1]
      if (hueco === 2) salida.push(ordenadas[i] - 1)
      else if (hueco > 2) salida.push(ELIPSIS)
    }
    salida.push(ordenadas[i])
  }
  return salida
}

/**
 * El rango que se está viendo: `[desde, hasta]`, 1-indexado e inclusivo, para "Mostrando 1–12
 * de 1.042".
 *
 * ⚠️ `hasta` se acota con `total` y no con `page * pageSize`: la última página casi nunca está
 * llena, y sin el `min` el pie diría "Mostrando 1.041–1.060 de 1.042".
 * Con `total = 0` devuelve `[0, 0]` — no `[1, 0]`, que se leería como un rango dado vuelta.
 */
export function rangoVisible(
  page: number,
  pageSize: number,
  total: number,
): [number, number] {
  if (total <= 0 || pageSize <= 0) return [0, 0]
  const actual = Math.max(Math.trunc(page), 1)
  const desde = (actual - 1) * pageSize + 1
  if (desde > total) return [0, 0]
  return [desde, Math.min(actual * pageSize, total)]
}
