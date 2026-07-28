"use client"

import { useEffect, useState } from "react"
import { Download } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { ErrorState } from "@/components/ui/ErrorState"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { Skeleton } from "@/components/ui/skeleton"
import { exportarEvaluadosResultados, fetchEvaluadosResultados } from "@/services/evaluacionReportes"
import type { EvaluadoListadoItem } from "@/types/evaluacionReportes"
import { EvaluadosResultadosTable } from "./EvaluadosResultadosTable"
import { FichaEvaluadoModal } from "./FichaEvaluadoModal"
import { useFiltrosEvaluadosResultados } from "./useFiltrosEvaluadosResultados"

export function EvaluadosResultadosPanel({ loteId }: { loteId: string }) {
  const [todos, setTodos] = useState<EvaluadoListadoItem[]>([])
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState(false)
  const [nonce, setNonce] = useState(0)
  const [fichaId, setFichaId] = useState<string | null>(null)
  const { campos, filtrados, filtros } = useFiltrosEvaluadosResultados(todos)

  useEffect(() => {
    setCargando(true)
    setError(false)
    fetchEvaluadosResultados(loteId, { proyecto_id: filtros.proyecto_id })
      .then((r) => setTodos(r.items))
      .catch(() => setError(true))
      .finally(() => setCargando(false))
    // proyecto es server-side (ver el hook): cambiarlo obliga a re-traer, a diferencia
    // de sector/perfil/nota, que se aplican sobre `todos` sin volver al backend.
  }, [loteId, nonce, filtros.proyecto_id])

  async function exportar() {
    try {
      await exportarEvaluadosResultados(loteId, "excel", filtros)
    } catch {
      toast.error("No se pudo exportar. Intentá de nuevo.")
    }
  }

  if (cargando) return <Skeleton className="h-64 w-full rounded-lg" />
  if (error) return <ErrorState action={() => setNonce((n) => n + 1)} />

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <FiltersBar campos={campos} />
        <Button variant="outline" onClick={exportar}><Download className="size-4" />Exportar</Button>
      </div>
      <EvaluadosResultadosTable items={filtrados} onFicha={setFichaId} />
      {fichaId && <FichaEvaluadoModal loteId={loteId} evaluadoId={fichaId} onClose={() => setFichaId(null)} />}
    </div>
  )
}
