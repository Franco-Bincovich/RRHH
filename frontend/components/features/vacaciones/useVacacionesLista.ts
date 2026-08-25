"use client"

/**
 * Estado y carga del listado de vacaciones TOMADAS (las que tienen fechas y viven en
 * solicitudes_vacaciones). Extraído de app/(dashboard)/vacaciones/page.tsx, que estaba en
 * 148/150 y no tenía margen para sumar la sección de días pendientes.
 *
 * Movido VERBATIM: el fetch, el reseteo de página, el manejo de error y la cancelación se
 * comportan igual que antes. La página queda como layout y sigue siendo dueña de `page`
 * (el hook de filtros la resetea a 1 vía onFiltroChange, contrato del bloque B).
 */
import { useState, useCallback, useEffect } from "react"
import { toast } from "sonner"

import { fetchVacaciones, cancelarVacacion, type VacacionesFiltros } from "@/services/vacaciones"
import type { SolicitudVacaciones } from "@/types/vacaciones"

export const PAGE_SIZE_INICIAL = 20

export function useVacacionesLista(filtros: VacacionesFiltros, page: number, pageSize: number) {
  const [solicitudes, setSolicitudes] = useState<SolicitudVacaciones[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [total, setTotal] = useState(0)
  const [cancelingId, setCancelingId] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const data = await fetchVacaciones(filtros, page, pageSize)
      setSolicitudes(data.items)
      setTotal(data.total)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
    // filtros es un objeto nuevo en cada render; se serializa para no re-fetchear de más.
  }, [JSON.stringify(filtros), page, pageSize])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  const handleCancel = useCallback(async (id: string) => {
    setCancelingId(id)
    try {
      await cancelarVacacion(id)
      await load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "No se pudo cancelar la solicitud. Intentá de nuevo.")
    } finally {
      setCancelingId(null)
    }
  }, [load])

  return { solicitudes, loading, error, total, cancelingId, load, handleCancel }
}
