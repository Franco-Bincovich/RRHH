"use client"

import { useCallback, useEffect, useState } from "react"

import { getCandidatos, type CandidatosFiltros } from "@/services/candidatos"
import type { CandidatoConGrupo } from "@/types/candidato"

interface UseCandidatos {
  candidatos: CandidatoConGrupo[]
  /** Total del FILTRO, no de la página: es lo que leen el encabezado y la barra de paginación. */
  total: number
  /** nombre de grupo → total en todo el filtro. Alimenta el encabezado de cada búsqueda. */
  conteoPorGrupo: Record<string, number>
  loading: boolean
  error: boolean
  refetch: () => void
}

/** Fetching de una página de candidatos con loading/error/refetch (patrón del proyecto). */
export function useCandidatos(
  filtros: CandidatosFiltros = {}, page = 1, pageSize = 20,
): UseCandidatos {
  const [candidatos, setCandidatos] = useState<CandidatoConGrupo[]>([])
  const [total, setTotal] = useState(0)
  const [conteoPorGrupo, setConteoPorGrupo] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const pagina = await getCandidatos(filtros, page, pageSize)
      setCandidatos(pagina.items)
      setTotal(pagina.total)
      setConteoPorGrupo(pagina.conteo_por_grupo)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
    // El hook NO conoce el reseteo de página: `page` entra como parámetro y volver a 1 al
    // cambiar un filtro es responsabilidad de la pantalla (invariante 4 del Bloque B). Si lo
    // hiciera acá, cualquier consumidor que quisiera conservar la página no podría.
  }, [filtros.sinVacante, filtros.clasificacion, page, pageSize])

  useEffect(() => {
    load()
  }, [load])

  return { candidatos, total, conteoPorGrupo, loading, error, refetch: load }
}
