"use client"

import { useState, useCallback, useEffect } from "react"
import { Plus } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { Pagination } from "@/components/ui/Pagination"
import { AusenciaModal } from "@/components/features/ausencias/AusenciaModal"
import { AusenciasTable } from "@/components/features/ausencias/AusenciasTable"
import { useFiltrosAusencias } from "@/components/features/ausencias/useFiltrosAusencias"
import { AdjuntosDialog } from "@/components/features/adjuntos/AdjuntosDialog"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { fetchAusencias, deleteAusencia, exportarAusencias } from "@/services/ausencias"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { Ausencia } from "@/types/ausencias"

const PAGE_SIZE = 20

export default function AusenciasPage() {
  const canWrite = useCanWrite()
  const [ausencias, setAusencias] = useState<Ausencia[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const [modalOpen, setModalOpen] = useState(false)
  const [editingAusencia, setEditingAusencia] = useState<Ausencia | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [docsFor, setDocsFor] = useState<Ausencia | null>(null)

  const { empresaActivaId, filtros, campos } = useFiltrosAusencias(() => setPage(1))

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const data = await fetchAusencias(filtros, page, PAGE_SIZE)
      setAusencias(data.items)
      setTotal(data.total)
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
    try {
      await deleteAusencia(id)
      await load()
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "No se pudo eliminar la ausencia. Intentá de nuevo.")
    } finally {
      setDeletingId(null)
    }
  }

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

  function handleModalSuccess() {
    handleModalClose()
    load()
  }

  return (
    <div>
      <PageHeader
        title="Ausencias"
        description={loading ? "Cargando..." : `${total} registro${total !== 1 ? "s" : ""}`}
        action={
          <div className="flex gap-2">
            {!loading && !error && ausencias.length > 0 && (
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

      <FiltersBar campos={campos} />

      <AusenciasTable
        items={ausencias}
        loading={loading}
        error={error}
        showEmpresa={!empresaActivaId}
        canWrite={canWrite}
        deletingId={deletingId}
        onRetry={load}
        onEdit={handleEdit}
        onDelete={handleDelete}
        onDocs={setDocsFor}
      />

      {!loading && !error && total > PAGE_SIZE && (
        <Pagination page={page} total={total} pageSize={PAGE_SIZE} onPageChange={setPage} />
      )}

      <AusenciaModal
        open={modalOpen}
        onClose={handleModalClose}
        onSuccess={handleModalSuccess}
        editing={editingAusencia}
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
