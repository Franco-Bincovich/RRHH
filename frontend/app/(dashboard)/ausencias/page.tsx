"use client"

import { useState } from "react"
import { Plus } from "lucide-react"

import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import { Pagination } from "@/components/ui/Pagination"
import { AusenciaModal } from "@/components/features/ausencias/AusenciaModal"
import { AusenciasTable } from "@/components/features/ausencias/AusenciasTable"
import { useFiltrosAusencias } from "@/components/features/ausencias/useFiltrosAusencias"
import { useListadoAusencias } from "@/components/features/ausencias/useListadoAusencias"
import { AdjuntosDialog } from "@/components/features/adjuntos/AdjuntosDialog"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { exportarAusencias } from "@/services/ausencias"
import { ConfirmDialog } from "@/components/ui/ConfirmDialog"
import { useConfirmacion } from "@/components/features/shared/useConfirmacion"
import { confirmarEliminarAusencia } from "@/components/features/shared/confirmaciones"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { Ausencia } from "@/types/ausencias"

/** Filas por página INICIAL: el selector de filas es parte del pie del patrón (§3), así que el
 *  valor deja de ser una constante fija y pasa a ser estado de la pantalla. */
const PAGE_SIZE_INICIAL = 20

export default function AusenciasPage() {
  const canWrite = useCanWrite()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(PAGE_SIZE_INICIAL)

  const [modalOpen, setModalOpen] = useState(false)
  const [editingAusencia, setEditingAusencia] = useState<Ausencia | null>(null)
  const [docsFor, setDocsFor] = useState<Ausencia | null>(null)

  const { empresaActivaId, filtros, campos } = useFiltrosAusencias(() => setPage(1))
  const { items, loading, error, total, deletingId, load, handleDelete } =
    useListadoAusencias(filtros, page, pageSize)

  /* 🔴 EL BORRADO PIDE CONFIRMACIÓN. `solicitudes_ausencia` no tiene baja lógica: el DELETE es
     físico, la fila desaparece y con ella los días que computaban al ausentismo del período.
     Un solo click no puede ser el único paso entre ver la tabla y perder ese dato. */
  const aBorrar = useConfirmacion<Ausencia>()

  const chips = chipsDeCampos(campos)

  function handleEdit(a: Ausencia) {
    setEditingAusencia(a)
    setModalOpen(true)
  }

  function handleNew() {
    setEditingAusencia(null)
    setModalOpen(true)
  }

  function handleModalClose() {
    setModalOpen(false)
    setEditingAusencia(null)
  }

  return (
    <div>
      <PageHeader
        title="Ausencias"
        /* El conteo sale de `total` (el del filtro entero, del backend) y no del largo de la
           página. Sólo la primerísima carga no tiene número que mostrar. */
        description={loading ? "Cargando..." : `${total} registro${total !== 1 ? "s" : ""}`}
        action={
          <div className="flex gap-2">
            {!loading && !error && items.length > 0 && (
              <ExportMenu onExport={(f) => exportarAusencias(f, filtros)} />
            )}
            {canWrite && (
              <Button className="min-h-11" onClick={handleNew}>
                <Plus className="size-4" />
                Registrar ausencia
              </Button>
            )}
          </div>
        }
      />

      {/* `panel`: la forma completa del patrón de filtros (caja propia, "Más filtros" y los chips
          de la fila inferior). `disabled` durante la carga: los controles quedan A LA VISTA con
          sus chips pero no se pueden tocar (§3) — vaciarlos le sacaría al usuario justo el filtro
          cuyo resultado está esperando. */}
      <FiltersBar campos={campos} panel disabled={loading} />

      <AusenciasTable
        items={items}
        loading={loading}
        error={error}
        showEmpresa={!empresaActivaId}
        canWrite={canWrite}
        deletingId={deletingId}
        onRetry={load}
        onEdit={handleEdit}
        onDelete={aBorrar.pedir}
        onDocs={setDocsFor}
        chips={chips}
        onLimpiarTodo={() => chips.forEach((c) => c.quitar())}
        accionVacio={canWrite ? (
          <Button className="min-h-11" onClick={handleNew}>Registrar la primera</Button>
        ) : undefined}
      />

      {/*
       * 🔴 EL PIE VA SIEMPRE QUE HAYA FILAS, no sólo cuando hay más de una página. Antes aparecía
       * con `total > PAGE_SIZE`: con pocos registros y un filtro puesto, la pantalla dejaba de
       * decir cuántos resultados había justo cuando el filtro es lo que hay que entender.
       * El total que muestra es el TOTAL FILTRADO del backend, no `items.length`.
       */}
      {!loading && !error && items.length > 0 && (
        <Pagination
          page={page} total={total} pageSize={pageSize} onPageChange={setPage}
          onPageSizeChange={(n) => { setPageSize(n); setPage(1) }}
        />
      )}

      <AusenciaModal
        open={modalOpen}
        onClose={handleModalClose}
        onSuccess={() => { handleModalClose(); load() }}
        editing={editingAusencia}
      />

      <ConfirmDialog
        open={aBorrar.abierto}
        onClose={aBorrar.cerrar}
        onConfirm={() => {
          const a = aBorrar.pendiente
          aBorrar.cerrar()
          if (a) handleDelete(a.id)
        }}
        loading={deletingId !== null}
        {...confirmarEliminarAusencia(aBorrar.pendiente ?? {})}
      />

      <AdjuntosDialog
        open={!!docsFor}
        onClose={() => setDocsFor(null)}
        entidad="ausencia"
        entidadId={docsFor?.id ?? ""}
        titulo={`Ausencia · ${docsFor?.empleado_nombre ?? ""}`}
      />
    </div>
  )
}
