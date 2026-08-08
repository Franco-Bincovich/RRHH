"use client"

import { useCallback, useEffect, useState } from "react"
import { Plus } from "lucide-react"
import { toast } from "sonner"
import { cn } from "@/lib/utils"
import { PageHeader } from "@/components/layout/PageHeader"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { KanbanView } from "@/components/features/objetivos/KanbanView"
import { ListView } from "@/components/features/objetivos/ListView"
import { ObjetivoModal } from "@/components/features/objetivos/ObjetivoModal"
import { ObjetivosFiltros } from "@/components/features/objetivos/ObjetivosFiltros"
import { ImportarObjetivosBoton } from "@/components/features/objetivos/ImportarObjetivosBoton"
import { ImportarObjetivosModal } from "@/components/features/objetivos/ImportarObjetivosModal"
import { ExportMenu } from "@/components/features/export/ExportMenu"
import { cambiarEstadoObjetivo, deleteObjetivo, exportarObjetivos, fetchObjetivos, fetchUsuariosActivos } from "@/services/objetivos"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { useCanWrite } from "@/hooks/useCanWrite"
import type { EstadoObjetivo, Objetivo, UserItem } from "@/types/objetivo"
import type { Empresa } from "@/types/empresa"

type Vista = "tablero" | "lista"

function TableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full rounded-lg" />
      ))}
    </div>
  )
}

export default function ObjetivosPage() {
  const canWrite = useCanWrite()
  const [empresaActivaId] = useState<string | null>(getEmpresaActivaId)
  const [vista, setVista]           = useState<Vista>("tablero")
  const [objetivos, setObjetivos]   = useState<Objetivo[]>([])
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
      <PageHeader title="Objetivos" description="Tablero de tareas del equipo de RRHH" />

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

      <div className="mb-4 flex gap-1 border-b border-border">
        {(["tablero", "lista"] as Vista[]).map((v) => (
          <button key={v} onClick={() => setVista(v)}
            className={cn("px-4 pb-3 pt-1 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              vista === v ? "border-b-2 border-primary text-primary" : "text-muted-foreground hover:text-foreground")}>
            {v === "tablero" ? "Tablero" : "Lista"}
          </button>
        ))}
      </div>

      {loading && <TableSkeleton />}
      {!loading && error && <div className="py-12 text-center text-sm text-destructive">Error al cargar. <button onClick={load} className="underline">Reintentar</button></div>}
      {!loading && !error && vista === "tablero" && (
        <KanbanView objetivos={objetivos} onMover={handleMover} moviendo={moviendo} canWrite={canWrite}
          onEdit={(o) => { setEditing(o); setModalOpen(true) }} onDelete={handleDelete} deletingId={deletingId} />
      )}
      {!loading && !error && vista === "lista" && (
        <ListView objetivos={objetivos} showEmpresa={mostrarEmpresa} canWrite={canWrite}
          onEdit={(o) => { setEditing(o); setModalOpen(true) }} onDelete={handleDelete} deletingId={deletingId} />
      )}

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
