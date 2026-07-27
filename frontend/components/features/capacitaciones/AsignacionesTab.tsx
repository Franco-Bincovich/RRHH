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
import { fetchAsignaciones, deleteAsignacion, exportarCapacitaciones } from "@/services/capacitaciones"
import type { Asignacion } from "@/types/capacitacion"

export function AsignacionesTab({ canWrite }: { canWrite: boolean }) {
  const [asignaciones, setAsignaciones] = useState<Asignacion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [asignacionModal, setAsignacionModal] = useState(false)
  const [estadoModal, setEstadoModal] = useState<Asignacion | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  // El listado no pagina, así que no hay page que resetear: el callback no tiene nada que hacer.
  const { empresaActivaId, filtros, campos } = useFiltrosAsignacionesCap(() => {})

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const data = await fetchAsignaciones(filtros)
      setAsignaciones(data.items)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
    // filtros es un objeto nuevo en cada render; se serializa para no re-fetchear de más.
  }, [JSON.stringify(filtros)])  // eslint-disable-line react-hooks/exhaustive-deps

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
          {!loading && !error && asignaciones.length > 0 && (
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
