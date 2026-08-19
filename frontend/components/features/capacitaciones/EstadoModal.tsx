"use client"

import { useState } from "react"
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select } from "@/components/ui/select"
import { updateAsignacion } from "@/services/capacitaciones"
import type { Asignacion, AsignacionUpdate } from "@/types/capacitacion"

interface Props {
  open: boolean
  asignacion: Asignacion
  onClose: () => void
  onSuccess: () => void
}

export function EstadoModal({ open, asignacion, onClose, onSuccess }: Props) {
  const [estado, setEstado] = useState<string>(asignacion.estado)
  const [fechaLimite, setFechaLimite] = useState(asignacion.fecha_limite ?? "")
  const [fechaCompletado, setFechaCompletado] = useState(asignacion.fecha_completado ?? "")
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState("")

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setServerError("")
    try {
      const payload: AsignacionUpdate = {
        estado: estado as AsignacionUpdate["estado"],
        fecha_limite: fechaLimite || undefined,
        fecha_completado: fechaCompletado || undefined,
      }
      await updateAsignacion(asignacion.id, payload)
      onSuccess()
    } catch (err: unknown) {
      setServerError(err instanceof Error ? err.message : "Error al actualizar")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Actualizar estado</DialogTitle>
        </DialogHeader>

        <form id="estado-form" onSubmit={handleSubmit} noValidate>
          <div className="flex flex-col gap-4 py-2">
            <p className="text-sm text-muted-foreground">
              {asignacion.empleado_nombre} — <span className="text-foreground">{asignacion.capacitacion_nombre}</span>
            </p>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="estado_sel">Estado</Label>
              <Select id="estado_sel" value={estado} onChange={(e) => setEstado(e.target.value)}>
                <option value="pendiente">Pendiente</option>
                <option value="en_curso">En curso</option>
                <option value="completado">Completado</option>
              </Select>
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="estado_limite">Fecha límite <span className="text-muted-foreground text-xs font-normal">(opcional)</span></Label>
              <Input id="estado_limite" type="date" value={fechaLimite} onChange={(e) => setFechaLimite(e.target.value)} />
            </div>

            {estado === "completado" && (
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="estado_completado">Fecha completado <span className="text-muted-foreground text-xs font-normal">(opcional — se usa hoy si se deja vacío)</span></Label>
                <Input id="estado_completado" type="date" value={fechaCompletado} onChange={(e) => setFechaCompletado(e.target.value)} />
              </div>
            )}

          </div>
          {serverError && <p className="mt-2 text-sm text-destructive" role="alert">{serverError}</p>}
        </form>

        <DialogFooter>
          <Button type="button" variant="outline" className="min-h-11" onClick={onClose} disabled={submitting}>Cancelar</Button>
          <Button type="submit" form="estado-form" className="min-h-11" disabled={submitting}>
            {submitting ? "Guardando..." : "Guardar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
