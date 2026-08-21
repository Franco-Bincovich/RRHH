"use client"

import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"
import { PageHeader } from "@/components/layout/PageHeader"
import { ObjetivoModal } from "@/components/features/objetivos/ObjetivoModal"
import { construirCampos } from "@/components/features/objetivos/_camposObjetivos"
import { FiltersBar } from "@/components/ui/FiltersBar"
import { chipsDeCampos } from "@/components/ui/filtrosChips"
import { ObjetivosVistas } from "@/components/features/objetivos/ObjetivosVistas"
import type { Vista } from "@/components/features/objetivos/ObjetivosVistas"
import { NuevoObjetivoBoton, ObjetivosAcciones } from "@/components/features/objetivos/ObjetivosAcciones"
import { ImportarObjetivosModal } from "@/components/features/objetivos/ImportarObjetivosModal"
import { cambiarEstadoObjetivo, deleteObjetivo, fetchObjetivos, fetchUsuariosActivos } from "@/services/objetivos"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { EstadoObjetivo, Objetivo, UserItem } from "@/types/objetivo"
import type { Empresa } from "@/types/empresa"

export default function ObjetivosPage() {
  const canWrite = useCanWrite()
  const [empresaActivaId] = useState<string | null>(getEmpresaActivaId)
  const [vista, setVista]           = useState<Vista>("tablero")
  const [objetivos, setObjetivos]   = useState<Objetivo[]>([])
  /**
   * 🔴 EL TOTAL LO DICE EL BACKEND, SIEMPRE — nunca `objetivos.length`.
   *
   * Hoy los dos números coinciden porque este listado es el único del sistema que no pagina
   * (`objetivo_repo.find_all` trae el árbol entero). El día que pagine —y el wrapper ya tiene la
   * forma final para eso— `items` pasa a ser una página y `length` diría "20" sobre 400 sin
   * dejar de compilar. Es el bug que `HorasTab` ya pagó una vez: mostraba "9 h" con 400 cargadas
   * porque sumaba con `.reduce()` sobre la página en lugar de leer el total.
   *
   * ⚠️ CUENTA RAÍCES, no objetivos: los subobjetivos viajan anidados en `hijos`, así que
   * `total` NO es la cantidad de filas del tablero ni siquiera hoy. El contador dice "objetivos
   * principales" por eso. El conteo aplanado es otra cosa y solo lo usa el tope de export.
   */
  const [total, setTotal]           = useState(0)
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState(false)
  const [empresas, setEmpresas]     = useState<Empresa[]>([])
  const [usuarios, setUsuarios]     = useState<UserItem[]>([])
  const [empresaFiltro, setEmpresaFiltro]     = useState("")
  const [estadoFiltro, setEstadoFiltro]       = useState("")
  const [prioridadFiltro, setPrioridadFiltro] = useState("")
  const [responsableFiltro, setResponsableFiltro] = useState("")
  const [modalOpen, setModalOpen]   = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [editing, setEditing]       = useState<Objetivo | null>(null)
  const [moviendo, setMoviendo]     = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    if (!empresaActivaId) fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
    fetchUsuariosActivos().then((r) => setUsuarios(r.items)).catch(() => {})
  }, [empresaActivaId])

  const load = useCallback(async () => {
    setLoading(true); setError(false)
    try {
      const override = !empresaActivaId && empresaFiltro ? empresaFiltro : undefined
      const data = await fetchObjetivos(override, estadoFiltro || undefined, responsableFiltro || undefined, prioridadFiltro || undefined)
      setObjetivos(data.items)
      setTotal(data.total)
    } catch { setError(true) }
    finally { setLoading(false) }
  }, [empresaActivaId, empresaFiltro, estadoFiltro, prioridadFiltro, responsableFiltro])

  useEffect(() => { load() }, [load])

  async function handleMover(id: string, estado: EstadoObjetivo) {
    setMoviendo(id)
    try { await cambiarEstadoObjetivo(id, { estado }); await load() }
    catch { toast.error("No se pudo mover el objetivo. Intentá de nuevo.") } finally { setMoviendo(null) }
  }

  async function handleDelete(id: string) {
    setDeletingId(id)
    try { await deleteObjetivo(id); await load() }
    catch { toast.error("No se pudo eliminar el objetivo. Intentá de nuevo.") } finally { setDeletingId(null) }
  }

  const mostrarEmpresa = !empresaActivaId
  const empresaDestino = empresaActivaId ?? (empresaFiltro || "")

  /* ⚠️ `onFiltroChange` queda vacío: **este listado no pagina** (el backend devuelve el árbol
     entero), así que no hay página que resetear. Se pasa igual para no divergir del molde y para
     el día que pagine — el wrapper ya tiene la forma final, ver `types/objetivo.ts`. */
  const campos = construirCampos({
    mostrarEmpresa, empresas, empresaFiltro, setEmpresaFiltro,
    estadoFiltro, setEstadoFiltro, prioridadFiltro, setPrioridadFiltro,
    usuarios, responsableFiltro, setResponsableFiltro, onFiltroChange: () => {},
  })
  const chips = chipsDeCampos(campos)
  const nuevoBtn = <NuevoObjetivoBoton onClick={() => { setEditing(null); setModalOpen(true) }} />

  return (
    <div>
      <PageHeader
        title="Objetivos"
        description={
          total === 0
            ? "Tablero de tareas del equipo de Capital Humano"
            : `${total} ${total === 1 ? "objetivo principal" : "objetivos principales"} · tablero del equipo de Capital Humano`
        }
      />

      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        {/* `panel`: la forma completa del patrón de filtros (caja propia, "Más filtros" y los
            chips de la fila inferior). Reemplaza a `ObjetivosFiltros`, que eran cuatro `<Select>`
            sueltos sin chips — su propio encabezado decía que migrarla "es un rediseño del filtro,
            no una división", y éste es ese rediseño. */}
        <div className="min-w-[18rem] flex-1"><FiltersBar campos={campos} panel disabled={loading} /></div>
        <ObjetivosAcciones
          canWrite={canWrite}
          empresaOverride={!empresaActivaId && empresaFiltro ? empresaFiltro : undefined}
          estado={estadoFiltro || undefined}
          responsable={responsableFiltro || undefined}
          prioridad={prioridadFiltro || undefined}
          sinEmpresa={!empresaDestino}
          onImportar={() => setImportOpen(true)}
          nuevoBtn={nuevoBtn}
        />
      </div>

      <ObjetivosVistas
        vista={vista} onVista={setVista} loading={loading} error={error} onReintentar={load}
        objetivos={objetivos} total={total} mostrarEmpresa={mostrarEmpresa} canWrite={canWrite}
        onMover={handleMover} moviendo={moviendo} deletingId={deletingId}
        onEdit={(o) => { setEditing(o); setModalOpen(true) }} onDelete={handleDelete}
        chips={chips}
        onLimpiarTodo={() => chips.forEach((c) => c.quitar())}
        accionVacio={canWrite ? nuevoBtn : undefined}
      />

      <ImportarObjetivosModal
        open={importOpen} empresaId={empresaDestino}
        onClose={() => setImportOpen(false)}
        onSuccess={() => { void load() }}
      />

      <ObjetivoModal open={modalOpen} onClose={() => { setModalOpen(false); setEditing(null) }}
        onSuccess={() => { setModalOpen(false); setEditing(null); load() }} editing={editing} />
    </div>
  )
}
