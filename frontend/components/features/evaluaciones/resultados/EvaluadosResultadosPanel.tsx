"use client"

import { useEffect, useState } from "react"
import { Download } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { ErrorState } from "@/components/ui/ErrorState"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { Pagination } from "@/components/ui/Pagination"
import { Skeleton } from "@/components/ui/skeleton"
import { exportarEvaluadosResultados, fetchEvaluadosResultados } from "@/services/evaluacionReportes"
import type { EvaluadoListadoItem } from "@/types/evaluacionReportes"
import { EvaluadosResultadosTable } from "./EvaluadosResultadosTable"
import { FichaEvaluadoModal } from "./FichaEvaluadoModal"
import { useFiltrosEvaluadosResultados } from "./useFiltrosEvaluadosResultados"

const PAGE_SIZE = 20

export function EvaluadosResultadosPanel({ loteId }: { loteId: string }) {
  const [items, setItems] = useState<EvaluadoListadoItem[]>([])
  const [total, setTotal] = useState(0)
  const [sectores, setSectores] = useState<string[]>([])
  const [page, setPage] = useState(1)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState(false)
  const [nonce, setNonce] = useState(0)
  const [fichaId, setFichaId] = useState<string | null>(null)
  const { campos, filtros } = useFiltrosEvaluadosResultados(sectores, () => setPage(1))

  useEffect(() => {
    setCargando(true)
    setError(false)
    fetchEvaluadosResultados(loteId, filtros, page, PAGE_SIZE)
      .then((r) => {
        setItems(r.items)
        setTotal(r.total)
        // 🔴 Las opciones del filtro salen de la RESPUESTA, no de `r.items`: son los sectores del
        // lote entero. Derivarlas de la página dejaría fuera del desplegable justo a los que hay
        // que ir a buscar — y encima cambiarían al pasar de página.
        setSectores(r.sectores)
      })
      .catch(() => setError(true))
      .finally(() => setCargando(false))
    // Los CUATRO filtros son server-side: cualquiera obliga a re-traer. Hasta el 15/8/2026 sólo
    // `proyecto_id` estaba acá y los otros tres se aplicaban sobre el array; ver el hook.
  }, [loteId, nonce, page, filtros.sector, filtros.perfil, filtros.con_nota, filtros.proyecto_id])

  async function exportar() {
    try {
      await exportarEvaluadosResultados(loteId, "excel", filtros)
    } catch {
      toast.error("No se pudo exportar. Intentá de nuevo.")
    }
  }

  if (error) return <ErrorState action={() => setNonce((n) => n + 1)} />

  return (
    <div>
      {/* La barra de filtros NO se esconde mientras carga: si desapareciera en cada fetch, el
          usuario perdería de vista qué filtro aplicó justo cuando espera su resultado. */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <FiltersBar campos={campos} />
        <Button variant="outline" onClick={exportar}><Download className="size-4" />Exportar</Button>
      </div>
      {cargando ? (
        <Skeleton className="mt-4 h-64 w-full rounded-lg" />
      ) : (
        <>
          <EvaluadosResultadosTable items={items} onFicha={setFichaId} />
          {total > PAGE_SIZE && (
            <Pagination page={page} total={total} pageSize={PAGE_SIZE} onPageChange={setPage} />
          )}
        </>
      )}
      {fichaId && <FichaEvaluadoModal loteId={loteId} evaluadoId={fichaId} onClose={() => setFichaId(null)} />}
    </div>
  )
}
