"use client"

import { useCallback, useEffect, useState } from "react"
import { Plus } from "lucide-react"
import { toast } from "sonner"
import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { ObjetivoModal } from "@/components/features/objetivos/ObjetivoModal"
import { ObjetivosFiltros } from "@/components/features/objetivos/ObjetivosFiltros"
import { ObjetivosVistas } from "@/components/features/objetivos/ObjetivosVistas"
import type { Vista } from "@/components/features/objetivos/ObjetivosVistas"
import { ImportarObjetivosBoton } from "@/components/features/objetivos/ImportarObjetivosBoton"
import { ImportarObjetivosModal } from "@/components/features/objetivos/ImportarObjetivosModal"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { cambiarEstadoObjetivo, deleteObjetivo, exportarObjetivos, fetchObjetivos, fetchUsuariosActivos } from "@/services/objetivos"
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

  return (
    <div>
      <PageHeader
        title="Objetivos"
        description={
          total === 0
            ? "Tablero de tareas del equipo de RRHH"
            : `${total} ${total === 1 ? "objetivo principal" : "objetivos principales"} · tablero del equipo de RRHH`
        }
      />

      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <ObjetivosFiltros
          mostrarEmpresa={mostrarEmpresa} empresas={empresas} usuarios={usuarios}
          empresaFiltro={empresaFiltro} setEmpresaFiltro={setEmpresaFiltro}
          estadoFiltro={estadoFiltro} setEstadoFiltro={setEstadoFiltro}
          prioridadFiltro={prioridadFiltro} setPrioridadFiltro={setPrioridadFiltro}
          responsableFiltro={responsableFiltro} setResponsableFiltro={setResponsableFiltro}
        />
        <div className="flex gap-2">
          <ExportMenu onExport={(f) => exportarObjetivos(f, !empresaActivaId && empresaFiltro ? empresaFiltro : undefined, estadoFiltro || undefined, responsableFiltro || undefined, prioridadFiltro || undefined)} />
          {/* La empresa del import sale del sidebar o del filtro: importar es una ACCIÓN y
              necesita una empresa concreta. En consolidado el botón queda deshabilitado. */}
          {canWrite && (
            <ImportarObjetivosBoton
              sinEmpresa={!empresaDestino}
              onClick={() => setImportOpen(true)}
            />
          )}
          {canWrite && (
            <Button className="min-h-11 gap-2" onClick={() => { setEditing(null); setModalOpen(true) }}>
              <Plus className="size-4" /> Nuevo objetivo
            </Button>
          )}
        </div>
      </div>

      <ObjetivosVistas
        vista={vista} onVista={setVista} loading={loading} error={error} onReintentar={load}
        objetivos={objetivos} total={total} mostrarEmpresa={mostrarEmpresa} canWrite={canWrite}
        onMover={handleMover} moviendo={moviendo} deletingId={deletingId}
        onEdit={(o) => { setEditing(o); setModalOpen(true) }} onDelete={handleDelete}
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
