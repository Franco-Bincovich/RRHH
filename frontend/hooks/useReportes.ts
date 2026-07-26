"use client"

import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"

import { exportarReporte, fetchHistorial, type HistorialItem } from "@/services/reportes"

// Estado del módulo de reportes: carga del historial + exportación (PDF/Excel) con su loading.
// La generación vive en cada tarjeta (ReporteCard) y avisa acá vía onGenerado → cargarHistorial.
export function useReportes() {
  const [historial, setHistorial] = useState<HistorialItem[]>([])
  const [historialLoading, setHistorialLoading] = useState(true)
  const [exportLoading, setExportLoading] = useState<Set<string>>(new Set())

  const cargarHistorial = useCallback(async () => {
    setHistorialLoading(true)
    try {
      setHistorial(await fetchHistorial())
    } catch {
      // no bloquear la UI si falla el historial
    } finally {
      setHistorialLoading(false)
    }
  }, [])

  useEffect(() => {
    cargarHistorial()
  }, [cargarHistorial])

  const exportar = useCallback(async (id: string, nombre: string, formato: "pdf" | "excel") => {
    const key = `${id}-${formato}`
    setExportLoading((prev) => new Set(prev).add(key))
    try {
      await exportarReporte(id, formato, nombre)
      toast.success(`${formato.toUpperCase()} descargado`)
    } catch {
      toast.error(`No se pudo exportar el ${formato.toUpperCase()}. Intentá de nuevo.`)
    } finally {
      setExportLoading((prev) => {
        const next = new Set(prev)
        next.delete(key)
        return next
      })
    }
  }, [])

  return { historial, historialLoading, exportLoading, cargarHistorial, exportar }
}
