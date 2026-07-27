"use client"

import { useState, useCallback, useEffect } from "react"
import { Umbrella, Plus } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/PageHeader"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { Pagination } from "@/components/ui/Pagination"
import { VacacionesModal } from "@/components/features/vacaciones/VacacionesModal"
import { VacacionesTable } from "@/components/features/vacaciones/VacacionesTable"
import { useFiltrosVacaciones } from "@/components/features/vacaciones/useFiltrosVacaciones"
import { AdjuntosDialog } from "@/components/features/adjuntos/AdjuntosDialog"
import { MapaVacaciones } from "@/components/features/vacaciones/MapaVacaciones"
import { fetchVacaciones, cancelarVacacion, exportarVacaciones } from "@/services/vacaciones"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { SolicitudVacaciones } from "@/types/vacaciones"

type Vista = "lista" | "mapa"

const PAGE_SIZE = 20

function TableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full rounded-lg" />
      ))}
    </div>
  )
}

export default function VacacionesPage() {
  const canWrite = useCanWrite()
  const [solicitudes, setSolicitudes] = useState<SolicitudVacaciones[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [vista, setVista] = useState<Vista>("lista")
  const [modalOpen, setModalOpen] = useState(false)
  const [cancelingId, setCancelingId] = useState<string | null>(null)
  const [docsFor, setDocsFor] = useState<SolicitudVacaciones | null>(null)

  const { empresaActivaId, filtros, campos } = useFiltrosVacaciones(() => setPage(1))

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const data = await fetchVacaciones(filtros, page, PAGE_SIZE)
      setSolicitudes(data.items)
      setTotal(data.total)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
    // filtros es un objeto nuevo en cada render; se serializa para no re-fetchear de más.
  }, [JSON.stringify(filtros), page])  // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])

  async function handleCancel(id: string) {
    setCancelingId(id)
    try {
      await cancelarVacacion(id)
      await load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "No se pudo cancelar la solicitud. Intentá de nuevo.")
    } finally {
      setCancelingId(null)
    }
  }

  return (
    <div>
      <PageHeader
        title="Vacaciones"
        description={loading ? "Cargando..." : `${total} registro${total !== 1 ? "s" : ""}`}
        action={
          <div className="flex gap-2">
            {!loading && !error && solicitudes.length > 0 && (
              <ExportMenu onExport={(f) => exportarVacaciones(f, filtros)} />
            )}
            {canWrite && (
              <Button className="min-h-11" onClick={() => setModalOpen(true)}>
                <Plus className="size-4" />
                Registrar vacaciones
              </Button>
            )}
          </div>
        }
      />

      <div className="mb-4 flex gap-1 rounded-lg bg-muted p-1 w-fit">
        <Button size="sm" variant={vista === "lista" ? "secondary" : "ghost"} onClick={() => setVista("lista")}>Lista</Button>
        <Button size="sm" variant={vista === "mapa" ? "secondary" : "ghost"} onClick={() => setVista("mapa")}>Mapa</Button>
      </div>

      <FiltersBar campos={campos} />

      {loading && <TableSkeleton />}
      {!loading && error && <ErrorState action={load} />}
      {!loading && !error && solicitudes.length === 0 && (
        <EmptyState icon={<Umbrella />} title="Sin resultados" description="No hay registros de vacaciones que coincidan con los filtros." />
      )}

      {!loading && !error && solicitudes.length > 0 && (
        vista === "lista" ? (
          <VacacionesTable
            items={solicitudes}
            canWrite={canWrite}
            showEmpresa={!empresaActivaId}
            cancelingId={cancelingId}
            onCancel={handleCancel}
            onDocs={setDocsFor}
          />
        ) : (
          <MapaVacaciones solicitudes={solicitudes} />
        )
      )}

      {!loading && !error && vista === "lista" && total > PAGE_SIZE && (
        <Pagination page={page} total={total} pageSize={PAGE_SIZE} onPageChange={setPage} />
      )}

      <VacacionesModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={() => { setModalOpen(false); load() }}
      />

      <AdjuntosDialog
        open={!!docsFor}
        onClose={() => setDocsFor(null)}
        entidad="vacacion"
        entidadId={docsFor?.id ?? ""}
        titulo={`Vacación · ${docsFor?.empleado_nombre ?? ""}`}
      />
    </div>
  )
}
