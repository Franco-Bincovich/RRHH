"use client"

import { useEffect, useState } from "react"
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { EmpleadoCombobox } from "@/components/features/shared/EmpleadoCombobox"
import { createAsignacion } from "@/services/capacitaciones"
import { fetchCapacitaciones } from "@/services/capacitaciones"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { AsignacionCreate, Capacitacion } from "@/types/capacitacion"
import type { Empresa } from "@/types/empresa"

interface Props {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

type FormData = {
  empresa_id: string
  capacitacion_id: string
  empleado_id: string
  fecha_asignacion: string
  fecha_limite: string
}

type FormErrors = Partial<Record<keyof FormData, string>>

const EMPTY: FormData = {
  empresa_id: "", capacitacion_id: "", empleado_id: "", fecha_asignacion: "", fecha_limite: "",
}

const SEL =
  "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 disabled:opacity-50"

function validate(form: FormData): FormErrors {
  const e: FormErrors = {}
  if (!form.empresa_id) e.empresa_id = "Requerido"
  if (!form.capacitacion_id) e.capacitacion_id = "Requerido"
  if (!form.empleado_id) e.empleado_id = "Requerido"
  return e
}

export function AsignacionModal({ open, onClose, onSuccess }: Props) {
  const [form, setForm] = useState<FormData>(EMPTY)
  const [errors, setErrors] = useState<FormErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState("")

  const [empresas, setEmpresas] = useState<Empresa[]>([])
  const [capacitaciones, setCapacitaciones] = useState<Capacitacion[]>([])
  const [loadingCap, setLoadingCap] = useState(false)

  useEffect(() => {
    if (!open) return
    setErrors({})
    setServerError("")
    setForm({ ...EMPTY, empresa_id: getEmpresaActivaId() ?? "" })
  }, [open])

  useEffect(() => {
    if (!open) return
    fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
  }, [open])

  useEffect(() => {
    if (!form.empresa_id) { setCapacitaciones([]); return }
    setLoadingCap(true)
    fetchCapacitaciones(form.empresa_id, true)
      .then((r) => setCapacitaciones(r.items))
      .catch(() => setCapacitaciones([]))
      .finally(() => setLoadingCap(false))
    // Los empleados ya no se precargan acá: los busca `EmpleadoCombobox` contra el backend.
  }, [form.empresa_id])

  function field(key: keyof FormData) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
      setForm((p) => ({ ...p, [key]: e.target.value }))
      if (errors[key]) setErrors((p) => ({ ...p, [key]: undefined }))
    }
  }

  function handleEmpresaChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setForm((p) => ({ ...p, empresa_id: e.target.value, capacitacion_id: "", empleado_id: "" }))
    setErrors((p) => ({ ...p, empresa_id: undefined, capacitacion_id: undefined, empleado_id: undefined }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errs = validate(form)
    if (Object.keys(errs).length > 0) { setErrors(errs); return }
    setSubmitting(true)
    setServerError("")
    try {
      const payload: AsignacionCreate = {
        capacitacion_id: form.capacitacion_id,
        empleado_id: form.empleado_id,
        fecha_asignacion: form.fecha_asignacion || undefined,
        fecha_limite: form.fecha_limite || undefined,
      }
      await createAsignacion(payload)
      onSuccess()
    } catch (err: unknown) {
      setServerError(err instanceof Error ? err.message : "Ocurrió un error al asignar")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      <DialogContent className="max-h-[90vh] max-w-lg overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Asignar capacitación</DialogTitle>
        </DialogHeader>

        <form id="asig-form" onSubmit={handleSubmit} noValidate>
          <div className="flex flex-col gap-4 py-2">

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="asig_empresa">Empresa <span className="text-destructive" aria-hidden>*</span></Label>
              <select id="asig_empresa" className={SEL} value={form.empresa_id} onChange={handleEmpresaChange} aria-required aria-invalid={Boolean(errors.empresa_id)}>
                <option value="">Seleccionar empresa</option>
                {empresas.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
              </select>
              {errors.empresa_id && <p className="text-xs text-destructive" role="alert">{errors.empresa_id}</p>}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="asig_cap">Capacitación <span className="text-destructive" aria-hidden>*</span></Label>
              <select id="asig_cap" className={SEL} value={form.capacitacion_id} onChange={field("capacitacion_id")} disabled={!form.empresa_id || loadingCap} aria-required aria-invalid={Boolean(errors.capacitacion_id)}>
                <option value="">
                  {!form.empresa_id ? "Seleccioná primero una empresa" : loadingCap ? "Cargando..." : "Seleccionar capacitación"}
                </option>
                {capacitaciones.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nombre}{c.categoria ? ` — ${c.categoria}` : ""}
                  </option>
                ))}
              </select>
              {errors.capacitacion_id && <p className="text-xs text-destructive" role="alert">{errors.capacitacion_id}</p>}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="asig_emp">Empleado <span className="text-destructive" aria-hidden>*</span></Label>
              <EmpleadoCombobox
                id="asig_emp" value={form.empleado_id} empresaId={form.empresa_id || undefined}
                disabled={!form.empresa_id} mensajeDeshabilitado="Seleccioná primero una empresa"
                invalid={Boolean(errors.empleado_id)}
                onChange={(emp) => {
                  setForm((p) => ({ ...p, empleado_id: emp?.id ?? "" }))
                  setErrors((p) => ({ ...p, empleado_id: undefined }))
                }}
              />
              {errors.empleado_id && <p className="text-xs text-destructive" role="alert">{errors.empleado_id}</p>}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="asig_desde">Fecha asignación <span className="text-muted-foreground text-xs font-normal">(opcional)</span></Label>
                <Input id="asig_desde" type="date" value={form.fecha_asignacion} onChange={field("fecha_asignacion")} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="asig_limite">Fecha límite <span className="text-muted-foreground text-xs font-normal">(opcional)</span></Label>
                <Input id="asig_limite" type="date" value={form.fecha_limite} onChange={field("fecha_limite")} />
              </div>
            </div>

          </div>
          {serverError && <p className="mt-2 text-sm text-destructive" role="alert">{serverError}</p>}
        </form>

        <DialogFooter>
          <Button type="button" variant="outline" className="min-h-11" onClick={onClose} disabled={submitting}>Cancelar</Button>
          <Button type="submit" form="asig-form" className="min-h-11" disabled={submitting}>
            {submitting ? "Asignando..." : "Asignar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
