"use client"

import { useCallback, useEffect, useState } from "react"

import { getCandidatos, type CandidatosFiltros } from "@/services/candidatos"
import type { CandidatoConGrupo } from "@/types/candidato"

interface UseCandidatos {
  candidatos: CandidatoConGrupo[]
  loading: boolean
  error: boolean
  refetch: () => void
}

/** Fetching de la lista de candidatos con loading/error/refetch (patrón del proyecto). */
export function useCandidatos(filtros: CandidatosFiltros = {}): UseCandidatos {
  const [candidatos, setCandidatos] = useState<CandidatoConGrupo[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      setCandidatos(await getCandidatos(filtros))
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [filtros.sinVacante, filtros.clasificacion])

  useEffect(() => {
    load()
  }, [load])

  return { candidatos, loading, error, refetch: load }
}
