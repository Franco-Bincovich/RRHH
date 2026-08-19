"use client"

import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Select } from "@/components/ui/select"
import type { Asignacion, HoraCreate } from "@/types/proyecto"

interface Props {
  open: boolean
  proyectoId: string
  asignaciones: Asignacion[]
  onClose: () => void
  onSave: (body: HoraCreate) => Promise<void>
}

const ARS = new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS", maximumFractionDigits: 0 })
const INPUT_CLS = "flex min-h-[2.75rem] w-full rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
const LABEL_CLS = "block text-xs font-medium text-foreground mb-1"

export function HoraModal({ open, asignaciones, onClose, onSave }: Props) {
  const [asignacionId, setAsignacionId] = useState("")
  const [fecha, setFecha]               = useState("")
  const [horas, setHoras]               = useState("1")
  const [descripcion, setDescripcion]   = useState("")
  const [saving, setSaving]             = useState(false)

  const asigSeleccionada = asignaciones.find((a) => a.id === asignacionId)

  useEffect(() => {
    if (!open) return
    setAsignacionId(""); setFecha(new Date().toISOString().slice(0, 10))
    setHoras("1"); setDescripcion("")
  }, [open])

  async function handleSubmit() {
    if (!asignacionId || !fecha || parseFloat(horas) <= 0) return
    setSaving(true)
    try {
      await onSave({
        asignacion_id: asignacionId,
        fecha,
        horas: parseFloat(horas),
        descripcion: descripcion || undefined,
      })
    } catch {
      toast.error("No se pudo registrar la hora. Intentá de nuevo.")
    } finally { setSaving(false) }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose() }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-base">Cargar horas</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 pt-2">
          <div>
            <label className={LABEL_CLS}>Empleado / Asignación</label>
            <Select value={asignacionId} onChange={(e) => setAsignacionId(e.target.value)}>
              <option value="">Seleccioná un empleado</option>
              {asignaciones.filter((a) => a.activo).map((a) => (
                <option key={a.id} value={a.id}>
                  {a.empleado_nombre ?? a.empleado_id} — {a.rol}
                  {a.empleado_empresa_nombre ? ` (${a.empleado_empresa_nombre})` : ""}
                </option>
              ))}
            </Select>
          </div>

          {asigSeleccionada && (
            <div className="rounded-lg bg-muted/50 px-3 py-2 text-xs text-muted-foreground">
              Valor/hora: <span className="font-medium text-foreground">{ARS.format(asigSeleccionada.valor_hora)}</span>
              {" "} — se congelará en el registro
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={LABEL_CLS}>Fecha del trabajo</label>
              <input type="date" className={INPUT_CLS} value={fecha} onChange={(e) => setFecha(e.target.value)} />
            </div>
            <div>
              <label className={LABEL_CLS}>Horas</label>
              <input type="number" min="0.5" step="0.5" className={INPUT_CLS} value={horas}
                onChange={(e) => setHoras(e.target.value)} />
            </div>
          </div>

          <div>
            <label className={LABEL_CLS}>Descripción (opcional)</label>
            <input className={INPUT_CLS} value={descripcion} onChange={(e) => setDescripcion(e.target.value)}
              placeholder="Tarea realizada…" />
          </div>

          {asigSeleccionada && parseFloat(horas) > 0 && (
            <p className="text-xs text-muted-foreground">
              Costo estimado: <span className="font-medium text-foreground">
                {ARS.format(asigSeleccionada.valor_hora * parseFloat(horas))}
              </span>
            </p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" size="sm" className="min-h-[2.75rem]" onClick={onClose}>Cancelar</Button>
            <Button size="sm" className="min-h-[2.75rem]" onClick={handleSubmit}
              disabled={saving || !asignacionId || !fecha || parseFloat(horas) <= 0}>
              {saving ? "Guardando…" : "Registrar horas"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
