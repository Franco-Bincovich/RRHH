"use client"

import { useState } from "react"
import { Umbrella, Plus } from "lucide-react"

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
import { useVacacionesLista, PAGE_SIZE } from "@/components/features/vacaciones/useVacacionesLista"
import { AdjuntosDialog } from "@/components/features/adjuntos/AdjuntosDialog"
import { MapaVacaciones } from "@/components/features/vacaciones/MapaVacaciones"
import { PendientesSection } from "@/components/features/vacaciones/PendientesSection"
import { exportarVacaciones } from "@/services/vacaciones"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { SolicitudVacaciones } from "@/types/vacaciones"

type Vista = "lista" | "mapa"

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
  const [page, setPage] = useState(1)
  const [vista, setVista] = useState<Vista>("lista")
  const [modalOpen, setModalOpen] = useState(false)
  const [docsFor, setDocsFor] = useState<SolicitudVacaciones | null>(null)
  // El modal puede crear en cualquiera de las dos tablas, así que al guardar se refrescan las dos.
  const [pendientesKey, setPendientesKey] = useState(0)

  const { empresaActivaId, filtros, campos } = useFiltrosVacaciones(() => setPage(1))
  const { solicitudes, loading, error, total, cancelingId, load, handleCancel } =
    useVacacionesLista(filtros, page)

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

      {vista === "lista" && <PendientesSection showEmpresa={!empresaActivaId} refreshKey={pendientesKey} />}

      <VacacionesModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={() => { setModalOpen(false); load(); setPendientesKey((k) => k + 1) }}
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
