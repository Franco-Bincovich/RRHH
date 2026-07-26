"use client"

import { useCallback, useEffect, useState } from "react"

import { deleteLoteEvaluacion, deleteLotesBulk, fetchLotesHistorial } from "@/services/evaluacionReportes"
import type { LoteEvaluacion, LotesBulkResult } from "@/types/evaluacionReportes"

// Datos del historial de importaciones: carga consolidada (todas las empresas) + borrado.
// El borrado NO depende de la empresa activa (el backend lo desacopló); `eliminar` normaliza
// el caso de 1 (DELETE) y el de varios (bulk) a un mismo LotesBulkResult clasificado.
export function useHistorialImportaciones() {
  const [lotes, setLotes] = useState<LoteEvaluacion[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState(false)

  const recargar = useCallback(() => {
    setCargando(true)
    setError(false)
    return fetchLotesHistorial()
      .then((r) => setLotes(r.items))
      .catch(() => setError(true))
      .finally(() => setCargando(false))
  }, [])

  useEffect(() => {
    void recargar()
  }, [recargar])

  const eliminar = useCallback(async (ids: string[]): Promise<LotesBulkResult> => {
    if (ids.length === 1) {
      try {
        await deleteLoteEvaluacion(ids[0])
        return { eliminados: ids, fallidos: [] }
      } catch (e) {
        return { eliminados: [], fallidos: [{ id: ids[0], motivo: e instanceof Error ? e.message : "No se pudo eliminar" }] }
      }
    }
    return deleteLotesBulk(ids)
  }, [])

  return { lotes, cargando, error, recargar, eliminar }
}
