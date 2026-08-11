"use client"

import { Plus, Search, Layers } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { AreaModal } from "@/components/features/areas/AreaModal"
import { AreasTabla } from "@/components/features/areas/AreasTabla"
import { useAreas } from "@/components/features/areas/useAreas"
import { AreaEliminarDialog } from "@/components/features/areas/AreaEliminarDialog"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { exportarAreas } from "@/services/areas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { useCanWrite } from "@/hooks/useCanWrite"

export default function AreasPage() {
  const canWrite = useCanWrite()
  const {
    areas, filtradas, loading, error, search, setSearch,
    modalOpen, setModalOpen, editing, confirmDelete, setConfirmDelete, deleting,
    load, handleDelete, openCreate, openEdit, onModalSuccess,
  } = useAreas()

  if (loading) {
    return (
      <div>
        <PageHeader title="Áreas" description="Cargando..." />
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full rounded-lg" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div>
        <PageHeader title="Áreas" />
        <ErrorState
          description="No se pudieron cargar las áreas."
          action={load}
        />
      </div>
    )
  }

  return (
    <div>
      <PageHeader
        title="Áreas"
        description={`${areas.length} área${areas.length !== 1 ? "s" : ""}`}
        action={
          <div className="flex items-center gap-2">
            {/* El MISMO filtro de empresa que el listado. ⚠️ El buscador de abajo es
                CLIENT-SIDE, así que el archivo trae todas las áreas de la empresa, no las que
                el buscador deja a la vista. Con 12 áreas es tolerable; el día que crezca, ese
                `search` tiene que pasar al backend (regla del bloque B). */}
            <ExportMenu
              onExport={(formato) => exportarAreas(formato, getEmpresaActivaId() ?? undefined)}
            />
            {canWrite && (
              <Button className="min-h-11" onClick={openCreate}>
                <Plus />
                Nueva área
              </Button>
            )}
          </div>
        }
      />

      <div className="mb-4">
        <div className="relative max-w-sm">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Buscar por nombre..."
            className="pl-8"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {filtradas.length === 0 ? (
        <EmptyState
          icon={<Layers />}
          title={search ? "Sin resultados" : "Sin áreas"}
          description={
            search
              ? "No hay áreas que coincidan con la búsqueda."
              : "Todavía no hay áreas registradas. Creá la primera."
          }
          action={
            !search && canWrite ? (
              <Button className="min-h-11" onClick={openCreate}>
                <Plus />
                Nueva área
              </Button>
            ) : undefined
          }
        />
      ) : (
        <AreasTabla areas={filtradas} canWrite={canWrite}
                    onEdit={openEdit} onDelete={setConfirmDelete} />
      )}

      <AreaModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={onModalSuccess}
        area={editing}
        empresaId={getEmpresaActivaId() ?? undefined}
      />

      <AreaEliminarDialog
        area={confirmDelete}
        eliminando={deleting}
        onCancel={() => setConfirmDelete(null)}
        onConfirm={handleDelete}
      />
    </div>
  )
}
