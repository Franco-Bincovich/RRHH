"use client"

/**
 * Carga del catálogo de ítems de inventario: la página, su total y el estado de carga.
 *
 * Salió de `useFiltrosItemsInv` al migrar la pantalla al patrón del bloque B: con el armado de
 * los `FiltroCampo` adentro, aquel archivo pasaba de las 80 líneas que un hook puede tener. El
 * corte es el mismo que ya tienen ausencias y vacaciones — allá vive "qué está elegido", acá
 * "qué llegó".
 *
 * 🔴 `page` y `pageSize` ENTRAN POR PARÁMETRO y no son estado de este hook: el reset a la página
 * 1 al cambiar un filtro (invariante 4 del bloque B) lo cablea la pestaña, que es la única que ve
 * las dos cosas a la vez.
 */
import { useCallback, useEffect, useState } from "react"

import { fetchItems, type ItemsFiltros } from "@/services/inventario"
import type { InventarioItem } from "@/types/inventario"

export function useListadoItemsInv(filtros: ItemsFiltros, page: number, pageSize: number) {
  const [items, setItems] = useState<InventarioItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [total, setTotal] = useState(0)

  const load = useCallback(async () => {
    setLoading(true); setError(false)
    try {
      const data = await fetchItems(filtros, page, pageSize)
      setItems(data.items)
      // El total sale del wrapper del backend, NUNCA de `data.items.length`.
      setTotal(data.total)
    } catch { setError(true) }
    finally { setLoading(false) }
    // filtros es un objeto nuevo por render; se serializa para no re-fetchear de más.
  }, [JSON.stringify(filtros), page, pageSize])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  return { items, loading, error, total, load }
}
