"use client"

import { Plus } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import { AreaModal } from "@/components/features/areas/AreaModal"
import { AreasTabla } from "@/components/features/areas/AreasTabla"
import { construirCampos } from "@/components/features/areas/_camposAreas"
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

  const campos = construirCampos({ search, setSearch })
  const chips = chipsDeCampos(campos)

  return (
    <div>
      <PageHeader
        title="Áreas"
        /* 🔴 EL CONTEO SALE DE `total` Y NO DE `areas.length`: `areas` es UNA PÁGINA, y con
           búsqueda el total es el del filtro. Leer el largo diría 20 sobre 58, y 3 sobre 3 al
           buscar. Sólo la primerísima carga no tiene número que mostrar. */
        description={loading && total === 0 ? "Cargando..." : `${total} área${total !== 1 ? "s" : ""}`}
        action={
          <div className="flex items-center gap-2">
            {/* 🔴 El MISMO `buscado` que filtra la pantalla, y la MISMA empresa del sidebar.
                Antes el buscador era local y el archivo salía con todo: buscabas 3 áreas y
                exportabas 58. (Ese buscador es server-side desde el 15/8/2026 — ver `useAreas`;
                el comentario que decía lo contrario acá quedó viejo y se corrigió.) */}
            <ExportMenu
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

      {/* `panel`: la forma completa del patrón de filtros (caja propia y los chips de la fila
          inferior). Un solo control, así que no hay "Más filtros" — ver `_camposAreas.ts`.
          `disabled` durante la carga: el control queda A LA VISTA con su chip pero no se puede
          tocar (§3); vaciarlo le sacaría al usuario justo el filtro cuyo resultado espera. */}
      <FiltersBar campos={campos} panel disabled={loading} />

      <AreasTabla
        areas={areas}
        loading={loading}
        error={error}
        canWrite={canWrite}
        onRetry={load}
        onEdit={openEdit}
        onDelete={setConfirmDelete}
        chips={chips}
        onLimpiarTodo={() => chips.forEach((c) => c.quitar())}
        accionVacio={canWrite ? (
          <Button className="min-h-11" onClick={openCreate}>Crear la primera</Button>
        ) : undefined}
      />

      {/*
       * 🔴 EL PIE VA SIEMPRE QUE HAYA FILAS, no sólo cuando hay más de una página (era
       * `total > PAGE_SIZE`): es lo que dice cuántos resultados dio la búsqueda, y ese número es
       * el que importa justo cuando hay una búsqueda puesta.
       * ⚠️ Y VA DETRÁS DE `!loading`: hasta ahora esta pantalla no podía dibujar el pie sobre el
       * esqueleto porque el `return` temprano de la carga se llevaba la página entera. Al mover
       * los estados adentro de la tabla, esa protección accidental desaparece — sin esta guarda,
       * la barra quedaría mostrando el total del pedido ANTERIOR mientras carga el nuevo.
       */}
      {!loading && !error && areas.length > 0 && (
        <Pagination page={page} total={total} pageSize={PAGE_SIZE} onPageChange={setPage} />
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
