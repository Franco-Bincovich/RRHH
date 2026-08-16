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
import { PAGE_SIZE, useAreas } from "@/components/features/areas/useAreas"
import { useAreasAcciones } from "@/components/features/areas/useAreasAcciones"
import { AreaEliminarDialog } from "@/components/features/areas/AreaEliminarDialog"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { exportarAreas } from "@/services/areas"
import { Pagination } from "@/components/ui/Pagination"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { useCanWrite } from "@/hooks/useCanWrite"

export default function AreasPage() {
  const canWrite = useCanWrite()
  const {
    areas, total, page, setPage, loading, error, search, setSearch, buscado, load,
  } = useAreas()
  // El ABM recarga la lista al crear, editar o borrar: las tres cambian el TOTAL, no sólo las
  // filas que se ven.
  const {
    modalOpen, setModalOpen, editing, confirmDelete, setConfirmDelete, deleting,
    handleDelete, openCreate, openEdit, onModalSuccess,
  } = useAreasAcciones(load)

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
        // `total` y no `areas.length`: `areas` es una página, y con búsqueda el total es el
        // del filtro. Leer el largo diría 20 sobre 58, y 3 sobre 3 al buscar.
        description={`${total} área${total !== 1 ? "s" : ""}`}
        action={
          <div className="flex items-center gap-2">
            {/* El MISMO filtro de empresa que el listado. ⚠️ El buscador de abajo es
                CLIENT-SIDE, así que el archivo trae todas las áreas de la empresa, no las que
                el buscador deja a la vista. Con 12 áreas es tolerable; el día que crezca, ese
                `search` tiene que pasar al backend (regla del bloque B). */}
            <ExportMenu
              // 🔴 El MISMO `buscado` que filtra la pantalla. Antes el buscador era local y el
              // archivo salía con todo: buscabas 3 áreas y exportabas 58.
              onExport={(formato) => exportarAreas(formato, getEmpresaActivaId() ?? undefined, buscado || undefined)}
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

      {total === 0 ? (
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
        <>
          <AreasTabla areas={areas} canWrite={canWrite}
                      onEdit={openEdit} onDelete={setConfirmDelete} />
          {total > PAGE_SIZE && (
            <Pagination page={page} total={total} pageSize={PAGE_SIZE} onPageChange={setPage} />
          )}
        </>
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
