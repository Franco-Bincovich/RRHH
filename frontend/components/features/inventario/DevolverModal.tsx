"use client"

import { useState } from "react"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select } from "@/components/ui/select"
import { devolverItem } from "@/services/inventario"
import type { Asignacion, DevolucionRequest, EstadoDevolucion } from "@/types/inventario"

interface Props {
  asignacion: Asignacion
  onClose: () => void
  onSuccess: () => void
}

export function DevolverModal({ asignacion, onClose, onSuccess }: Props) {
  const [estado, setEstado] = useState<EstadoDevolucion>("ok")
  const [notas, setNotas] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState("")

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true); setServerError("")
    try {
      const payload: DevolucionRequest = { estado_devolucion: estado, notas: notas.trim() || undefined }
      await devolverItem(asignacion.id, payload)
      onSuccess()
    } catch (err: unknown) {
      setServerError(err instanceof Error ? err.message : "Error al registrar la devolución")
    } finally { setSubmitting(false) }
  }

  return (
    <Dialog open onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      <DialogContent className="max-w-sm">
        <DialogHeader><DialogTitle>Registrar devolución</DialogTitle></DialogHeader>
        <form id="dev-form" onSubmit={handleSubmit} noValidate>
          <div className="flex flex-col gap-4 py-2">
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">{asignacion.item_nombre}</span>
              {" "}devuelto por{" "}
              <span className="font-medium text-foreground">{asignacion.empleado_nombre}</span>
            </p>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="dev_estado">Estado de devolución</Label>
              <Select id="dev_estado" value={estado} onChange={(e) => setEstado(e.target.value as EstadoDevolucion)}>
                <option value="ok">OK — sin daños</option>
                <option value="con_daño">Con daño → pasa a reparación</option>
              </Select>
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="dev_notas">Notas <span className="text-xs text-muted-foreground font-normal">(opcional)</span></Label>
              <Textarea id="dev_notas" value={notas} onChange={(e) => setNotas(e.target.value)} rows={2} className="resize-none" placeholder="ej. Pantalla rayada" />
            </div>
          </div>
          {serverError && <p className="mt-2 text-sm text-destructive" role="alert">{serverError}</p>}
        </form>
        <DialogFooter>
          <Button type="button" variant="outline" className="min-h-11" onClick={onClose} disabled={submitting}>Cancelar</Button>
          <Button type="submit" form="dev-form" className="min-h-11" disabled={submitting}>{submitting ? "Guardando..." : "Registrar devolución"}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
