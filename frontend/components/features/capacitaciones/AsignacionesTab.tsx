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
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import { Pagination } from "@/components/ui/Pagination"
import { fetchAsignaciones, deleteAsignacion, exportarCapacitaciones } from "@/services/capacitaciones"
import type { Asignacion } from "@/types/capacitacion"

const PAGE_SIZE_INICIAL = 20

export function AsignacionesTab({ canWrite }: { canWrite: boolean }) {
  const [asignaciones, setAsignaciones] = useState<Asignacion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [asignacionModal, setAsignacionModal] = useState(false)
  const [estadoModal, setEstadoModal] = useState<Asignacion | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(PAGE_SIZE_INICIAL)
  const [total, setTotal] = useState(0)
  // 🔴 Cambiar cualquier filtro vuelve a la página 1 (invariante 4 del bloque B): filtrar
  // parado en la 7 pediría una página que el resultado nuevo no tiene y la tabla saldría
  // vacía sobre un filtro que sí tiene filas.
  const { empresaActivaId, filtros, campos } = useFiltrosAsignacionesCap(() => setPage(1))
  const chips = chipsDeCampos(campos)

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const data = await fetchAsignaciones(filtros, page, pageSize)
      // El total sale del wrapper del backend, NUNCA de `data.items.length`.
      setAsignaciones(data.items); setTotal(data.total)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
    // filtros es un objeto nuevo en cada render; se serializa para no re-fetchear de más.
  }, [JSON.stringify(filtros), page, pageSize])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  async function handleDelete(id: string) {
    setDeletingId(id)
    try { await deleteAsignacion(id); await load() }
    catch { toast.error("No se pudo eliminar la asignación. Intentá de nuevo.") }
    finally { setDeletingId(null) }
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        {/* `panel`: la forma completa del patrón de filtros (caja propia, "Más filtros" y los
            chips de la fila inferior). Antes era la barra simple, sin chips, con los CINCO
            controles a la vista tapando la tabla. */}
        <div className="min-w-[18rem] flex-1"><FiltersBar campos={campos} panel disabled={loading} /></div>
        <div className="flex gap-2">
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
        chips={chips}
        onLimpiarTodo={() => chips.forEach((c) => c.quitar())}
        accionVacio={canWrite ? (
          <Button className="min-h-11" onClick={() => setAsignacionModal(true)}>Asignar la primera</Button>
        ) : undefined}
      />

      {/*
       * 🔴 ESTA BARRA NO EXISTÍA, Y SU AUSENCIA ERA UN BUG. La pestaña ya llevaba `page` y `total`
       * y ya pedía de a 20 al backend, pero **nunca renderizaba `<Pagination>`** —el import estaba
       * puesto y sin usar—: con más de 20 asignaciones cargadas, las que sobraban eran
       * INALCANZABLES desde la UI y no había ninguna señal de que existieran. El pie va siempre
       * que haya filas y sólo después de cargar; el total es el del backend, no
       * `asignaciones.length`.
       */}
      {!loading && !error && asignaciones.length > 0 && (
        <Pagination page={page} total={total} pageSize={pageSize} onPageSizeChange={setPageSize} onPageChange={setPage} />
      )}

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
