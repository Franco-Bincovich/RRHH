"use client"

import { useCallback, useEffect, useState } from "react"
import { Plus } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { AsignacionesCapTable } from "@/components/features/capacitaciones/AsignacionesCapTable"
import { AsignacionModal } from "@/components/features/capacitaciones/AsignacionModal"
import { EstadoModal } from "@/components/features/capacitaciones/EstadoModal"
import { useFiltrosAsignacionesCap } from "@/components/features/capacitaciones/useFiltrosAsignacionesCap"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { Pagination } from "@/components/ui/Pagination"
import { fetchAsignaciones, deleteAsignacion, exportarCapacitaciones } from "@/services/capacitaciones"
import type { Asignacion } from "@/types/capacitacion"

const PAGE_SIZE = 20

export function AsignacionesTab({ canWrite }: { canWrite: boolean }) {
  const [asignaciones, setAsignaciones] = useState<Asignacion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [asignacionModal, setAsignacionModal] = useState(false)
  const [estadoModal, setEstadoModal] = useState<Asignacion | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  // 🔴 Cambiar cualquier filtro vuelve a la página 1 (invariante 4 del bloque B): filtrar
  // parado en la 7 pediría una página que el resultado nuevo no tiene y la tabla saldría
  // vacía sobre un filtro que sí tiene filas.
  const { empresaActivaId, filtros, campos } = useFiltrosAsignacionesCap(() => setPage(1))

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const data = await fetchAsignaciones(filtros, page, PAGE_SIZE)
      setAsignaciones(data.items); setTotal(data.total)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
    // filtros es un objeto nuevo en cada render; se serializa para no re-fetchear de más.
  }, [JSON.stringify(filtros), page])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  async function handleDelete(id: string) {
    setDeletingId(id)
    try { await deleteAsignacion(id); await load() }
    catch { toast.error("No se pudo eliminar la asignación. Intentá de nuevo.") }
    finally { setDeletingId(null) }
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <FiltersBar campos={campos} />
        <div className="mb-4 flex gap-2">
          {/* `total` y no `asignaciones.length`: en la página 2+ el largo de la página no dice
              si hay algo que exportar — lo dice el total del filtro. */}
          {!loading && !error && total > 0 && (
            <ExportMenu onExport={(f) => exportarCapacitaciones(f, filtros)} />
          )}
          {canWrite && (
            <Button className="min-h-11" onClick={() => setAsignacionModal(true)}>
              <Plus className="size-4" /> Asignar
            </Button>
          )}
        </div>
      </div>

      <AsignacionesCapTable
        asignaciones={asignaciones} loading={loading} error={error} canWrite={canWrite}
        mostrarEmpresa={!empresaActivaId} deletingId={deletingId} onReload={load}
        onEditarEstado={setEstadoModal} onEliminar={handleDelete}
      />

      <AsignacionModal
        open={asignacionModal}
        onClose={() => setAsignacionModal(false)}
        onSuccess={() => { setAsignacionModal(false); load() }}
      />

      {estadoModal && (
        <EstadoModal
          open={Boolean(estadoModal)}
          asignacion={estadoModal}
          onClose={() => setEstadoModal(null)}
          onSuccess={() => { setEstadoModal(null); load() }}
        />
      )}
    </div>
  )
}
