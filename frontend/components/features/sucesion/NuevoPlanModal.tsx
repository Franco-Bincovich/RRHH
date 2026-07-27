"use client"

import { useEffect, useState } from "react"

import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { SELECT_CLASS } from "./_sucesion_ui"
import { fetchEmpleados } from "@/services/empleados"
import { createPlanCarrera } from "@/services/sucesion"
import type { Empleado } from "@/types/empleado"

const FORM_VACIO = { empleado_id: "", cargo_objetivo: "", fecha_objetivo: "", readiness: 0 }

export function NuevoPlanModal({
  open, onOpenChange, onCreado,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreado: () => void
}) {
  const [empleados, setEmpleados] = useState<Empleado[]>([])
  const [form, setForm]           = useState(FORM_VACIO)
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState<string | null>(null)

  // Al abrir: form limpio y lista de empleados activos fresca (igual que el openPlan viejo).
  useEffect(() => {
    if (!open) return
    setForm(FORM_VACIO)
    setError(null)
    fetchEmpleados({ page: 1, pageSize: 100, estado: "activo" })
      .then((res) => setEmpleados(res.items))
      .catch(() => setEmpleados([]))
  }, [open])

  async function handleSubmit() {
    if (!form.empleado_id) { setError("Seleccioná un empleado."); return }
    if (!form.cargo_objetivo.trim()) { setError("El cargo objetivo es requerido."); return }
    setLoading(true)
    setError(null)
    try {
      await createPlanCarrera({
        empleado_id: form.empleado_id,
        cargo_objetivo: form.cargo_objetivo.trim(),
        fecha_objetivo: form.fecha_objetivo || null,
        readiness: form.readiness,
      })
      onOpenChange(false)
      onCreado()
    } catch {
      setError("No se pudo crear el plan. Intentá de nuevo.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onOpenChange(false) }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Nuevo plan de carrera</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <Label htmlFor="plan-empleado">
              Empleado <span className="text-destructive" aria-hidden>*</span>
            </Label>
            <select
              id="plan-empleado"
              value={form.empleado_id}
              onChange={(e) => { setForm((p) => ({ ...p, empleado_id: e.target.value })); setError(null) }}
              className={`h-9 w-full ${SELECT_CLASS}`}
            >
              <option value="">Seleccioná un empleado</option>
              {empleados.map((emp) => (
                <option key={emp.id} value={emp.id}>
                  {emp.nombre} {emp.apellido} — {emp.roles?.[0] ?? emp.cargo}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="plan-cargo">
              Cargo objetivo <span className="text-destructive" aria-hidden>*</span>
            </Label>
            <Input
              id="plan-cargo"
              value={form.cargo_objetivo}
              onChange={(e) => { setForm((p) => ({ ...p, cargo_objetivo: e.target.value })); setError(null) }}
              placeholder="Ej. Tech Lead, Gerente de Producto…"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="plan-fecha">
              Fecha objetivo <span className="text-muted-foreground">(opcional)</span>
            </Label>
            <Input
              id="plan-fecha"
              type="date"
              value={form.fecha_objetivo}
              onChange={(e) => setForm((p) => ({ ...p, fecha_objetivo: e.target.value }))}
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="plan-readiness">Readiness inicial</Label>
              <span className="text-sm font-semibold tabular-nums text-foreground">
                {form.readiness}%
              </span>
            </div>
            <input
              id="plan-readiness"
              type="range"
              min={0}
              max={100}
              step={5}
              value={form.readiness}
              onChange={(e) => setForm((p) => ({ ...p, readiness: Number(e.target.value) }))}
              className="h-2 w-full cursor-pointer accent-primary"
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>0%</span><span>50%</span><span>100%</span>
            </div>
          </div>

          {error && <p className="text-xs text-destructive">{error}</p>}
        </div>

        <DialogFooter>
          <Button variant="outline" className="min-h-11" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancelar
          </Button>
          <Button className="min-h-11" onClick={handleSubmit} disabled={loading}>
            {loading ? "Guardando…" : "Crear plan"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
