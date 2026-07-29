"use client"

import { useState, useEffect, useMemo } from "react"

import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { createVacacion, fetchSaldoVacaciones } from "@/services/vacaciones"
import { getEmpresaActivaId } from "@/services/empresaStore"
import { getRol } from "@/services/permisos"
import { SeleccionEmpleado } from "@/components/features/shared/SeleccionEmpleado"
import { SaldoResumen } from "./SaldoResumen"
import { CamposVacacion } from "./CamposVacacion"
import { createVacacionPendiente } from "@/services/vacacionesPendientes"
import {
  EMPTY_VACACION, diasDelForm, payloadPendiente, payloadTomada, validateVacacion,
  type VacacionFormData, type VacacionFormErrors,
} from "./vacacionesForm"
import type { SaldoVacaciones } from "@/types/vacaciones"

interface VacacionesModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

export function VacacionesModal({ open, onClose, onSuccess }: VacacionesModalProps) {
  const isMando = getRol() === "mandos_medios"
  const [form, setForm] = useState<VacacionFormData>(EMPTY_VACACION)
  const [errors, setErrors] = useState<VacacionFormErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState("")
  const [saldo, setSaldo] = useState<SaldoVacaciones | null>(null)

  useEffect(() => {
    if (!open) return
    setForm({ ...EMPTY_VACACION, empresa_id: isMando ? "" : (getEmpresaActivaId() ?? "") })
    setErrors({})
    setServerError("")
    setSaldo(null)
  }, [open, isMando])

  useEffect(() => {
    if (!form.empleado_id) { setSaldo(null); return }
    fetchSaldoVacaciones(form.empleado_id, form.empresa_id || undefined)
      .then(setSaldo)
      .catch(() => setSaldo(null))
  }, [form.empleado_id])

  const diasSolicitados = useMemo(() => diasDelForm(form), [form])

  function field(key: keyof VacacionFormData) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
      setForm((prev) => ({ ...prev, [key]: e.target.value }))
      if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }))
    }
  }

  function toggle(key: "pendiente" | "liquidada") {
    return (e: React.ChangeEvent<HTMLInputElement>) => {
      setForm((prev) => ({ ...prev, [key]: e.target.checked }))
      setErrors({})
    }
  }

  function handleEmpresaChange(empresaId: string) {
    setForm((prev) => ({ ...prev, empresa_id: empresaId, empleado_id: "" }))
    setErrors((prev) => ({ ...prev, empresa_id: undefined, empleado_id: undefined }))
    setSaldo(null)
  }

  function handleEmpleadoChange(empleadoId: string) {
    setForm((prev) => ({ ...prev, empleado_id: empleadoId }))
    if (errors.empleado_id) setErrors((prev) => ({ ...prev, empleado_id: undefined }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errs = validateVacacion(form, !isMando)
    if (Object.keys(errs).length > 0) { setErrors(errs); return }
    setSubmitting(true)
    setServerError("")
    try {
      // El tilde "No se tomó" decide la TABLA, no solo los campos: sin fechas el registro va
      // a vacaciones_pendientes (ver backend/migrations/083).
      if (form.pendiente) await createVacacionPendiente(payloadPendiente(form))
      else await createVacacion(payloadTomada(form))
      onSuccess()
    } catch (err: unknown) {
      setServerError(err instanceof Error ? err.message : "Ocurrió un error al guardar")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      <DialogContent className="max-h-[90vh] max-w-lg overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{form.pendiente ? "Registrar días pendientes" : "Registrar vacaciones"}</DialogTitle>
        </DialogHeader>

        <form id="vacaciones-form" onSubmit={handleSubmit} noValidate>
          <div className="flex flex-col gap-4 py-2">
            <SeleccionEmpleado
              isMando={isMando}
              empresaId={form.empresa_id}
              empleadoId={form.empleado_id}
              onEmpresaChange={handleEmpresaChange}
              onEmpleadoChange={handleEmpleadoChange}
              errorEmpresa={errors.empresa_id}
              errorEmpleado={errors.empleado_id}
            />

            {saldo && <SaldoResumen saldo={saldo} diasSolicitados={diasSolicitados} tipo={form.tipo} />}

            <CamposVacacion form={form} errors={errors} field={field} toggle={toggle} />
          </div>

          {serverError && <p className="mt-2 text-sm text-destructive" role="alert">{serverError}</p>}
        </form>

        <DialogFooter>
          <Button type="button" variant="outline" className="min-h-11" onClick={onClose} disabled={submitting}>Cancelar</Button>
          <Button type="submit" form="vacaciones-form" className="min-h-11" disabled={submitting}>
            {submitting ? "Guardando..." : "Registrar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
