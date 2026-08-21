"use client"

import { useCallback, useEffect, useState } from "react"
import { Plus } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import { construirCamposCatalogo } from "@/components/features/capacitaciones/_camposCapacitaciones"
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
  /*
   * 🔴 EL FILTRO SE GUARDA COMO TEXTO ("" | "todos") Y NO COMO BOOLEAN: los chips del patrón se
   * derivan de un `FiltroCampo`, y el único control que puede expresar esto es un `select`, que
   * trabaja con strings. La traducción a `solo_activos: boolean` —lo único que el backend
   * entiende— se hace UNA vez, abajo. El default vacío significa "sólo activos", que es el
   * default del propio backend (`Query(True)`).
   */
  const [activosFiltro, setActivosFiltro] = useState("")
  const soloActivos = activosFiltro !== "todos"
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

  /* ⚠️ Esta pestaña NO PAGINA —`GET /api/capacitaciones` no acepta `page`— así que no hay página
     que resetear y `onFiltroChange` queda vacío. Se pasa igual para no divergir del molde y para
     el día que el backend pagine. Por lo mismo, la pestaña no tiene pie. */
  const campos = construirCamposCatalogo({
    empresaActivaId, empresas, empresaFiltro, setEmpresaFiltro,
    activosFiltro, setActivosFiltro, onFiltroChange: () => {},
  })
  const chips = chipsDeCampos(campos)

  async function handleDelete(id: string) {
    setDeletingId(id)
    try { await deleteCapacitacion(id); await load() }
    catch { toast.error("No se pudo eliminar el curso. Intentá de nuevo.") }
    finally { setDeletingId(null) }
  }

  // La empresa del import sale del sidebar o del filtro: importar es una ACCIÓN y necesita una
  // empresa concreta — es contra ese padrón que se matchean los colaboradores y contra ese
  // catálogo que se decide qué cursos crear. En consolidado el botón queda deshabilitado.
  const empresaDestino = empresaActivaId ?? (empresaFiltro || "")

  const nuevoBtn = (
    <Button className="min-h-11" onClick={() => { setEditing(null); setModalOpen(true) }}>
      <Plus className="size-4" />
      Nuevo curso
    </Button>
  )

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        {/* `panel`: la forma completa del patrón de filtros. Reemplaza al `<Select>` suelto y al
            checkbox "Solo activos", que quedaba activo SIN chip. */}
        <div className="min-w-[18rem] flex-1"><FiltersBar campos={campos} panel disabled={loading} /></div>
        <div className="flex flex-wrap items-center gap-2">
          {/* Los MISMOS filtros que el listado (empresa + solo activos): el archivo no puede
              traer las inactivas que la tabla está ocultando. */}
          <ExportMenu
            onExport={(f) => exportarCatalogoCapacitaciones(f, empresaActivaId ?? empresaFiltro ?? undefined, soloActivos)}
          />
        {canWrite && (
          <>
            <ImportarFormacionBoton
              sinEmpresa={!empresaDestino}
              onClick={() => setImportOpen(true)}
            />
            {nuevoBtn}
          </>
        )}
        </div>
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
        chips={chips}
        onLimpiarTodo={() => chips.forEach((c) => c.quitar())}
        accionVacio={canWrite ? nuevoBtn : undefined}
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
