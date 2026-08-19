"use client"

import { useCallback, useEffect, useState } from "react"
import { Plus } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Select } from "@/components/ui/select"
import { CapacitacionModal } from "@/components/features/capacitaciones/CapacitacionModal"
import { CatalogoTabla } from "@/components/features/capacitaciones/CatalogoTabla"
import { ImportarFormacionBoton } from "@/components/features/capacitaciones/ImportarFormacionBoton"
import { ImportarFormacionModal } from "@/components/features/capacitaciones/ImportarFormacionModal"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { fetchCapacitaciones, deleteCapacitacion, exportarCatalogoCapacitaciones } from "@/services/capacitaciones"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Capacitacion } from "@/types/capacitacion"
import type { Empresa } from "@/types/empresa"

/**
 * Catálogo de cursos: filtros, acciones y carga. Los cuatro estados de render viven en
 * `CatalogoTabla`, que es el reparto que `AsignacionesTab`/`AsignacionesCapTable` ya usaban.
 */
export function CatalogoTab({ canWrite }: { canWrite: boolean }) {
  const [empresaActivaId] = useState<string | null>(getEmpresaActivaId)
  const [capacitaciones, setCapacitaciones] = useState<Capacitacion[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [empresaFiltro, setEmpresaFiltro] = useState("")
  const [soloActivos, setSoloActivos] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [editing, setEditing] = useState<Capacitacion | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    if (!empresaActivaId) fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
  }, [empresaActivaId])

  const load = useCallback(async () => {
    setLoading(true)
    setError(false)
    try {
      const override = !empresaActivaId && empresaFiltro ? empresaFiltro : undefined
      const data = await fetchCapacitaciones(override, soloActivos)
      setCapacitaciones(data.items)
    } catch {
      setError(true)
    } finally {
      setLoading(false)
    }
  }, [empresaActivaId, empresaFiltro, soloActivos])

  useEffect(() => { load() }, [load])

  async function handleDelete(id: string) {
    setDeletingId(id)
    try { await deleteCapacitacion(id); await load() }
    catch { toast.error("No se pudo eliminar el curso. Intentá de nuevo.") }
    finally { setDeletingId(null) }
  }

  const mostrarFiltroEmpresa = !empresaActivaId && empresas.length > 0
  // La empresa del import sale del sidebar o del filtro: importar es una ACCIÓN y necesita una
  // empresa concreta — es contra ese padrón que se matchean los colaboradores y contra ese
  // catálogo que se decide qué cursos crear. En consolidado el botón queda deshabilitado.
  const empresaDestino = empresaActivaId ?? (empresaFiltro || "")

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          {mostrarFiltroEmpresa && (
            <Select size="sm" className="w-auto" aria-label="Filtrar por empresa" value={empresaFiltro} onChange={(e) => setEmpresaFiltro(e.target.value)}>
              <option value="">Todas las empresas</option>
              {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
            </Select>
          )}
          <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer select-none">
            <input type="checkbox" checked={soloActivos} onChange={(e) => setSoloActivos(e.target.checked)} className="h-4 w-4 rounded border border-input accent-primary" />
            Solo activos
          </label>
          {/* Los MISMOS filtros que el listado (empresa + solo activos): el archivo no puede
              traer las inactivas que la tabla está ocultando. */}
          <ExportMenu
            onExport={(f) => exportarCatalogoCapacitaciones(f, empresaActivaId ?? empresaFiltro ?? undefined, soloActivos)}
          />
        </div>
        {canWrite && (
          <div className="flex flex-wrap items-center gap-2">
            <ImportarFormacionBoton
              sinEmpresa={!empresaDestino}
              onClick={() => setImportOpen(true)}
            />
            <Button className="min-h-11" onClick={() => { setEditing(null); setModalOpen(true) }}>
              <Plus className="size-4" />
              Nuevo curso
            </Button>
          </div>
        )}
      </div>

      <CatalogoTabla
        capacitaciones={capacitaciones}
        loading={loading}
        error={error}
        onReintentar={load}
        canWrite={canWrite}
        deletingId={deletingId}
        onEditar={(c) => { setEditing(c); setModalOpen(true) }}
        onEliminar={handleDelete}
        mostrarEmpresa={!empresaActivaId}
      />

      <ImportarFormacionModal
        open={importOpen}
        empresaId={empresaDestino}
        onClose={() => setImportOpen(false)}
        onSuccess={() => { void load() }}
      />

      <CapacitacionModal
        open={modalOpen}
        onClose={() => { setModalOpen(false); setEditing(null) }}
        onSuccess={() => { setModalOpen(false); setEditing(null); load() }}
        editing={editing}
      />
    </div>
  )
}
