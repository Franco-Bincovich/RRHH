"use client"

import { useCallback, useEffect, useState } from "react"

import { getCriterioScreening, restaurarCriterioScreening, setCriterioScreening } from "@/services/screening"
import type { ScreeningCriterio, ScreeningCriterioResponse } from "@/types/screening"

const VACIO: ScreeningCriterioResponse = {
  def_relevante: "", def_dudoso: "", def_no_relevante: "", instrucciones: "", es_propia: false,
}

/**
 * Estado del criterio del clasificador de CVs.
 *
 * `es_propia` viene del backend y NO se deriva acá: dice si la empresa tiene fila propia o está
 * heredando la global. La pantalla lo necesita porque guardar mientras heredás te desengancha, y
 * "restaurar defaults" es exactamente volver a heredar (el backend borra la fila propia).
 */
export function useCriterioScreening() {
  const [criterio, setCriterio] = useState<ScreeningCriterioResponse>(VACIO)
  const [loading, setLoading] = useState(true)
  const [guardando, setGuardando] = useState(false)
  const [error, setError] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      setCriterio(await getCriterioScreening())
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const guardar = useCallback(async (datos: ScreeningCriterio): Promise<boolean> => {
    setGuardando(true)
    try {
      setCriterio(await setCriterioScreening(datos))
      return true
    } catch {
      return false
    } finally {
      setGuardando(false)
    }
  }, [])

  const restaurar = useCallback(async (): Promise<boolean> => {
    setGuardando(true)
    try {
      setCriterio(await restaurarCriterioScreening())
      return true
    } catch {
      return false
    } finally {
      setGuardando(false)
    }
  }, [])

  return { criterio, loading, guardando, error, guardar, restaurar }
}
