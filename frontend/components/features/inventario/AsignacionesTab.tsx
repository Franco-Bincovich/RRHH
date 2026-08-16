"use client"

import { useCallback, useEffect, useState } from "react"
import { Plus } from "lucide-react"

import { Button } from "@/components/ui/button"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { Pagination } from "@/components/ui/Pagination"
import { AsignacionesInvTable } from "@/components/features/inventario/AsignacionesInvTable"
import { AsignarModal } from "@/components/features/inventario/AsignarModal"
import { DevolverModal } from "@/components/features/inventario/DevolverModal"
import { useFiltrosAsignacionesInv } from "@/components/features/inventario/useFiltrosAsignacionesInv"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { exportarInventarioAsignaciones, fetchAsignaciones } from "@/services/inventario"
import type { Asignacion } from "@/types/inventario"

const PAGE_SIZE = 20

export function AsignacionesTab({ canWrite }: { canWrite: boolean }) {
  const [asignaciones, setAsignaciones] = useState<Asignacion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [asignarModal, setAsignarModal] = useState(false)
  const [devolviendo, setDevolviendo] = useState<Asignacion | null>(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  // 🔴 Cambiar cualquier filtro vuelve a la página 1 (invariante 4 del bloque B): filtrar
  // parado en la 7 pediría una página que el resultado nuevo no tiene y la tabla saldría
  // vacía sobre un filtro que sí tiene filas.
  const { empresaActivaId, filtros, campos } = useFiltrosAsignacionesInv(() => setPage(1))

  const load = useCallback(async () => {
    setLoading(true); setError(false)
    try {
      const data = await fetchAsignaciones(filtros, page, PAGE_SIZE)
      setAsignaciones(data.items); setTotal(data.total)
    } catch { setError(true) }
    finally { setLoading(false) }
    // filtros es un objeto nuevo por render; se serializa para no re-fetchear de más.
  }, [JSON.stringify(filtros), page])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <FiltersBar campos={campos} />
        <div className="mb-4 flex gap-2">
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
      />

      {total > PAGE_SIZE && (
        <Pagination page={page} total={total} pageSize={PAGE_SIZE} onPageChange={setPage} />
      )}

      <AsignarModal open={asignarModal} onClose={() => setAsignarModal(false)} onSuccess={() => { setAsignarModal(false); load() }} />
      {devolviendo && (
        <DevolverModal asignacion={devolviendo} onClose={() => setDevolviendo(null)} onSuccess={() => { setDevolviendo(null); load() }} />
      )}
    </div>
  )
}
