"use client"

/**
 * Estado y carga del listado de ausencias, más el borrado de una fila.
 *
 * Extraído de `app/(dashboard)/ausencias/page.tsx` al migrarla al patrón del bloque B: la página
 * estaba en 141/150 y lo que el patrón le suma —los chips, la acción del vacío, el estado del
 * selector de filas— no entraba. Se movió VERBATIM: el mismo fetch, el mismo manejo de error y el
 * mismo toast del borrado. Molde: `useVacacionesLista`, el hermano de la pantalla de al lado.
 *
 * 🔴 `page` y `pageSize` SIGUEN SIENDO DE LA PÁGINA y entran por parámetro. El hook de filtros los
 * resetea a 1 vía `onFiltroChange` (invariante 4 del bloque B) y ese cableado vive arriba; un hook
 * que fuera dueño de la página tendría que enterarse de cada filtro para saber cuándo resetear.
 */
import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"

import { deleteAusencia, fetchAusencias, type AusenciasFiltros } from "@/services/ausencias"
import type { Ausencia } from "@/types/ausencias"

export function useListadoAusencias(filtros: AusenciasFiltros, page: number, pageSize: number) {
  const [items, setItems] = useState<Ausencia[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [total, setTotal] = useState(0)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const data = await fetchAusencias(filtros, page, pageSize)
      setItems(data.items)
      // 🔴 El total sale del wrapper del backend, NUNCA de `data.items.length`: con paginación el
      // largo de la página es 20 y el pie diría "Mostrando 1–20 de 20" con 400 filas cargadas.
      setTotal(data.total)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
    // filtros es un objeto nuevo en cada render; se serializa para no re-fetchear de más.
  }, [JSON.stringify(filtros), page, pageSize])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  const handleDelete = useCallback(async (id: string) => {
    setDeletingId(id)
    try {
      await deleteAusencia(id)
      await load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "No se pudo eliminar la ausencia. Intentá de nuevo.")
    } finally {
      setDeletingId(null)
    }
  }, [load])

  return { items, loading, error, total, deletingId, load, handleDelete }
}
