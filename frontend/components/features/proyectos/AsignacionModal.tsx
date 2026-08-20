"use client"

import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import type { Asignacion, AsignacionUpdate } from "@/types/proyecto"

interface Props {
  open: boolean
  asignacion: Asignacion | null
  onClose: () => void
  onSave: (body: AsignacionUpdate) => Promise<void>
}

const INPUT_CLS = "flex min-h-[2.75rem] w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
const LABEL_CLS = "block text-xs font-medium text-foreground mb-1"

/** Edición de UNA asignación existente (rol/valor/fechas). El alta multi va en AsignarEmpleadosModal. */
export function AsignacionModal({ open, asignacion, onClose, onSave }: Props) {
  const [rol, setRol]               = useState("")
  const [valorHora, setValorHora]   = useState("0")
  const [fechaDesde, setFechaDesde] = useState("")
  const [fechaHasta, setFechaHasta] = useState("")
  const [saving, setSaving]         = useState(false)

  useEffect(() => {
    if (!open || !asignacion) return
    setRol(asignacion.rol)
    setValorHora(String(asignacion.valor_hora))
    setFechaDesde(asignacion.fecha_desde ?? "")
    setFechaHasta(asignacion.fecha_hasta ?? "")
  }, [open, asignacion])

  async function handleSubmit() {
    if (!rol.trim()) return
    setSaving(true)
    try {
      await onSave({
        rol: rol.trim(),
        valor_hora: parseFloat(valorHora) || 0,
        fecha_desde: fechaDesde || undefined,
        fecha_hasta: fechaHasta || undefined,
      })
    } catch {
      toast.error("No se pudo guardar la asignación. Intentá de nuevo.")
    } finally { setSaving(false) }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose() }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="text-base">Editar asignación</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 pt-2">
          <p className="text-sm text-muted-foreground">
            <span className="font-medium text-foreground">{asignacion?.empleado_nombre}</span>
            {asignacion?.empleado_empresa_nombre ? ` · ${asignacion.empleado_empresa_nombre}` : ""}
          </p>
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2 sm:col-span-1">
              <label className={LABEL_CLS}>Rol en el proyecto</label>
              <input className={INPUT_CLS} value={rol} onChange={(e) => setRol(e.target.value)} placeholder="Ej: Desarrollador" />
            </div>
            <div className="col-span-2 sm:col-span-1">
              <label className={LABEL_CLS}>Valor/hora (ARS)</label>
              <input type="number" min="0" step="100" className={INPUT_CLS} value={valorHora}
                onChange={(e) => setValorHora(e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={LABEL_CLS}>Desde</label>
              <input type="date" className={INPUT_CLS} value={fechaDesde} onChange={(e) => setFechaDesde(e.target.value)} />
            </div>
            <div>
              <label className={LABEL_CLS}>Hasta</label>
              <input type="date" className={INPUT_CLS} value={fechaHasta} onChange={(e) => setFechaHasta(e.target.value)} />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" className="min-h-[2.75rem]" onClick={onClose}>Cancelar</Button>
            <Button size="sm" className="min-h-[2.75rem]" onClick={handleSubmit} disabled={saving || !rol.trim()}>
              {saving ? "Guardando…" : "Guardar"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
