"use client"

import { useEffect, useState } from "react"
import { Download } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { ErrorState } from "@/components/ui/ErrorState"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import { Pagination } from "@/components/ui/Pagination"
import { exportarEvaluadosResultados, fetchEvaluadosResultados } from "@/services/evaluacionReportes"
import type { EvaluadoListadoItem } from "@/types/evaluacionReportes"
import { EvaluadosResultadosTable } from "./EvaluadosResultadosTable"
import { FichaEvaluadoModal } from "./FichaEvaluadoModal"
import { useFiltrosEvaluadosResultados } from "./useFiltrosEvaluadosResultados"

const PAGE_SIZE_INICIAL = 20

export function EvaluadosResultadosPanel({ loteId }: { loteId: string }) {
  const [items, setItems] = useState<EvaluadoListadoItem[]>([])
  const [total, setTotal] = useState(0)
  const [sectores, setSectores] = useState<string[]>([])
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(PAGE_SIZE_INICIAL)
  const [cargando, setCargando] = useState(true)
  const [error, setError] = useState(false)
  const [nonce, setNonce] = useState(0)
  const [fichaId, setFichaId] = useState<string | null>(null)
  const { campos, filtros } = useFiltrosEvaluadosResultados(sectores, () => setPage(1))
  const chips = chipsDeCampos(campos)

  useEffect(() => {
    setCargando(true)
    setError(false)
    fetchEvaluadosResultados(loteId, filtros, page, pageSize)
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
  }, [loteId, nonce, page, pageSize, filtros.sector, filtros.perfil, filtros.con_nota, filtros.proyecto_id])

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
      <div className="flex flex-wrap items-start justify-between gap-3">
        {/* `panel`: la forma completa del patrón de filtros (caja propia, "Más filtros" y los
            chips de la fila inferior). `disabled` durante la carga: los controles quedan A LA
            VISTA con sus chips pero no se pueden tocar (§3) — que es exactamente lo que el
            comentario de acá arriba ya pedía, ahora con el mecanismo del patrón. */}
        <div className="min-w-[18rem] flex-1"><FiltersBar campos={campos} panel disabled={cargando} /></div>
        <Button variant="outline" onClick={exportar}><Download className="size-4" />Exportar</Button>
      </div>

      <EvaluadosResultadosTable
        items={items} loading={cargando} onFicha={setFichaId}
        chips={chips} onLimpiarTodo={() => chips.forEach((c) => c.quitar())}
      />

      {/* 🔴 EL PIE VA SIEMPRE QUE HAYA FILAS (era `total > pageSize`) y sólo después de cargar:
          sin la guarda, al cambiar de filtro la barra queda mostrando el total del pedido
          ANTERIOR sobre el esqueleto. El total es el del backend, no `items.length`. */}
      {!cargando && items.length > 0 && (
        <Pagination page={page} total={total} pageSize={pageSize} onPageSizeChange={setPageSize} onPageChange={setPage} />
      )}
      {fichaId && <FichaEvaluadoModal loteId={loteId} evaluadoId={fichaId} onClose={() => setFichaId(null)} />}
    </div>
  )
}
