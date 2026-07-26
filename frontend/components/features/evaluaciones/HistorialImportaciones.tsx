"use client"

import { useState } from "react"
import { toast } from "sonner"
import { ClipboardList, Trash2 } from "lucide-react"

import { Button } from "@/components/ui/button"
import { ConfirmDialog } from "@/components/ui/ConfirmDialog"
import { EmptyState } from "@/components/ui/EmptyState"
import { ErrorState } from "@/components/ui/ErrorState"
import { Skeleton } from "@/components/ui/skeleton"
import { useHistorialImportaciones } from "@/hooks/useHistorialImportaciones"
import { HistorialTable } from "./HistorialTable"

// Historial de importaciones (tab "Importaciones"): lista consolidada + multi-selección + baja.
// No replica la guarda de empresa activa: el backend desacopló el borrado del header.
export function HistorialImportaciones() {
  const { lotes, cargando, error, recargar, eliminar } = useHistorialImportaciones()
  const [seleccion, setSeleccion] = useState<Set<string>>(new Set())
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [borrando, setBorrando] = useState(false)

  function toggle(id: string) {
    setSeleccion((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  function toggleAll() {
    setSeleccion((prev) => (prev.size === lotes.length ? new Set() : new Set(lotes.map((l) => l.id))))
  }

  const seleccionados = lotes.filter((l) => seleccion.has(l.id))
  const n = seleccionados.length
  const periodos = seleccionados.map((l) => l.periodo).join(", ")

  async function confirmar() {
    setBorrando(true)
    try {
      const r = await eliminar(seleccionados.map((l) => l.id))
      if (r.eliminados.length > 0) {
        toast.success(`${r.eliminados.length} importación${r.eliminados.length > 1 ? "es" : ""} eliminada${r.eliminados.length > 1 ? "s" : ""}`)
      }
      if (r.fallidos.length > 0) {
        toast.error(`No se pudieron eliminar ${r.fallidos.length}: ${r.fallidos.map((f) => f.motivo).join("; ")}`)
      }
      setSeleccion(new Set())
      setConfirmOpen(false)
      await recargar()
    } catch {
      toast.error("No se pudo completar el borrado. Intentá de nuevo.")
    } finally {
      setBorrando(false)
    }
  }

  if (cargando) return <Skeleton className="h-64 w-full rounded-lg" />
  if (error) return <ErrorState action={recargar} />
  if (lotes.length === 0) {
    return (
      <EmptyState
        icon={<ClipboardList />}
        title="Todavía no hay importaciones"
        description="Cuando importes un ciclo desde “Importar resultados”, va a aparecer acá."
      />
    )
  }

  return (
    <div className="space-y-4">
      {n > 0 && (
        <div className="flex items-center justify-between rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-2.5">
          <span className="text-sm text-foreground">{n} seleccionada{n > 1 ? "s" : ""}</span>
          <Button variant="destructive" className="min-h-11 gap-2" onClick={() => setConfirmOpen(true)}>
            <Trash2 className="size-4" /> Eliminar {n} importación{n > 1 ? "es" : ""}
          </Button>
        </div>
      )}

      <HistorialTable items={lotes} seleccion={seleccion} onToggle={toggle} onToggleAll={toggleAll} />

      <ConfirmDialog
        open={confirmOpen}
        onClose={() => setConfirmOpen(false)}
        onConfirm={confirmar}
        title="Eliminar importaciones"
        description={`Vas a eliminar ${n} importación${n > 1 ? "es" : ""}: ${periodos}. Esta acción no se puede deshacer.`}
        confirmLabel={`Sí, eliminar ${n > 1 ? `las ${n}` : "la importación"}`}
        cancelLabel="Cancelar"
        loading={borrando}
      />
    </div>
  )
}
