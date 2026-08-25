"use client"

import { useCallback, useEffect, useState } from "react"
import { Plus } from "lucide-react"

import { Button } from "@/components/ui/button"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import { Pagination } from "@/components/ui/Pagination"
import { AsignacionesInvTable } from "@/components/features/inventario/AsignacionesInvTable"
import { AsignarModal } from "@/components/features/inventario/AsignarModal"
import { DevolverModal } from "@/components/features/inventario/DevolverModal"
import { useFiltrosAsignacionesInv } from "@/components/features/inventario/useFiltrosAsignacionesInv"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { exportarInventarioAsignaciones, fetchAsignaciones } from "@/services/inventario"
import type { Asignacion } from "@/types/inventario"

const PAGE_SIZE_INICIAL = 20

export function AsignacionesTab({ canWrite }: { canWrite: boolean }) {
  const [asignaciones, setAsignaciones] = useState<Asignacion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [asignarModal, setAsignarModal] = useState(false)
  const [devolviendo, setDevolviendo] = useState<Asignacion | null>(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(PAGE_SIZE_INICIAL)
  const [total, setTotal] = useState(0)
  // 🔴 Cambiar cualquier filtro vuelve a la página 1 (invariante 4 del bloque B): filtrar
  // parado en la 7 pediría una página que el resultado nuevo no tiene y la tabla saldría
  // vacía sobre un filtro que sí tiene filas.
  const { empresaActivaId, filtros, campos } = useFiltrosAsignacionesInv(() => setPage(1))
  const chips = chipsDeCampos(campos)

  const load = useCallback(async () => {
    setLoading(true); setError(false)
    try {
      const data = await fetchAsignaciones(filtros, page, pageSize)
      // El total sale del wrapper del backend, NUNCA de `data.items.length`.
      setAsignaciones(data.items); setTotal(data.total)
    } catch { setError(true) }
    finally { setLoading(false) }
    // filtros es un objeto nuevo por render; se serializa para no re-fetchear de más.
  }, [JSON.stringify(filtros), page, pageSize])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        {/* `panel`: la forma completa del patrón de filtros (caja propia, "Más filtros" y los
            chips de la fila inferior). Antes era la barra simple, sin chips. */}
        <div className="min-w-[18rem] flex-1"><FiltersBar campos={campos} panel disabled={loading} /></div>
        <div className="flex gap-2">
          <ExportMenu onExport={(f) => exportarInventarioAsignaciones(f, filtros)} />
          {canWrite && (
            <Button className="min-h-11" onClick={() => setAsignarModal(true)}>
              <Plus className="size-4" /> Asignar ítem
            </Button>
          )}
        </div>
      </div>

      <AsignacionesInvTable
        asignaciones={asignaciones} loading={loading} error={error} canWrite={canWrite}
        mostrarEmpresa={!empresaActivaId} onReload={load} onDevolver={setDevolviendo}
        chips={chips}
        onLimpiarTodo={() => chips.forEach((c) => c.quitar())}
        accionVacio={canWrite ? (
          <Button className="min-h-11" onClick={() => setAsignarModal(true)}>Asignar el primero</Button>
        ) : undefined}
      />

      {/* 🔴 EL PIE VA SIEMPRE QUE HAYA FILAS (era `total > pageSize`) y sólo después de cargar:
          sin la guarda, la barra queda mostrando el total del pedido ANTERIOR sobre el esqueleto.
          El total es el del backend, no `asignaciones.length`. */}
      {!loading && !error && asignaciones.length > 0 && (
        <Pagination page={page} total={total} pageSize={pageSize} onPageSizeChange={setPageSize} onPageChange={setPage} />
      )}

      <AsignarModal open={asignarModal} onClose={() => setAsignarModal(false)} onSuccess={() => { setAsignarModal(false); load() }} />
      {devolviendo && (
        <DevolverModal asignacion={devolviendo} onClose={() => setDevolviendo(null)} onSuccess={() => { setDevolviendo(null); load() }} />
      )}
    </div>
  )
}
