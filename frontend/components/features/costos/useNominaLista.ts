"use client"

import { useCallback, useEffect, useState } from "react"

import { fetchNominaMes } from "@/services/costos"
import type { Nomina } from "@/types/costo"

export const PAGE_SIZE = 20

/**
 * El detalle de nómina de un período: su página y su total.
 *
 * Salió de `costos/page.tsx` al partirla (624 → orquestador). Va en un hook y no en el
 * componente porque la carga se prueba sin renderizar — vitest corre sin jsdom. La EDICIÓN vive
 * en `useEdicionNomina`: son dos ciclos de vida distintos y juntas pasaban el límite de 80.
 *
 * 🔴 `total` VIENE DEL BACKEND, no de `filas.length`. `filas` es una página de 20; el encabezado
 * dice cuántos registros tiene el período. Es la regla del molde: con paginación, todo agregado
 * sale del servidor (ver `components/ui/paginacionTotales.test.ts`).
 */
export function useNominaLista(mes: number, anio: number) {
  const [filas, setFilas] = useState<Nomina[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const data = await fetchNominaMes(mes, anio, page, PAGE_SIZE)
      setFilas(data.items)
      setTotal(data.total)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [mes, anio, page])

  useEffect(() => { load() }, [load])

  // Cambiar de período es cambiar de conjunto: quedarse en la página 7 pediría una que el mes
  // nuevo puede no tener, y la tabla saldría vacía sobre un mes que sí tiene nómina.
  useEffect(() => { setPage(1) }, [mes, anio])

  return { filas, total, page, setPage, loading, error, load }
}
