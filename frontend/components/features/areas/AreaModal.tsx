"use client"

import { useState, useEffect } from "react"

import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { fetchEmpleados } from "@/services/empleados"
import { createArea, updateArea } from "@/services/areas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Empleado } from "@/types/empleado"
import type { Area, AreaCreate } from "@/types/area"

interface AreaModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
  area?: Area
  /** empresa_id explícito (tab de empresa). Si no se pasa, usa la empresa activa. */
  empresaId?: string
}

type FormData = {
  nombre: string
  descripcion: string
  responsable_id: string
}

type FormErrors = Partial<Record<keyof FormData, string>>

const EMPTY: FormData = { nombre: "", descripcion: "", responsable_id: "" }

const SELECT_CLASS =
  "h-8 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50"

function validate(form: FormData): FormErrors {
  const errors: FormErrors = {}
  if (!form.nombre.trim()) errors.nombre = "El nombre es requerido"
  else if (form.nombre.trim().length > 100) errors.nombre = "Máximo 100 caracteres"
  return errors
}

export function AreaModal({ open, onClose, onSuccess, area, empresaId }: AreaModalProps) {
  const isEdit = Boolean(area)
  const [form, setForm]             = useState<FormData>(EMPTY)
  const [errors, setErrors]         = useState<FormErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState("")
  const [empleados, setEmpleados]   = useState<Empleado[]>([])

  useEffect(() => {
    if (!open) return
    fetchEmpleados({ page: 1, pageSize: 100, estado: "activo", empresaId })
      .then((res) => setEmpleados(res.items))
      .catch(() => setEmpleados([]))
  }, [open, empresaId])

  useEffect(() => {
    if (area) {
      setForm({
        nombre: area.nombre,
        descripcion: area.descripcion ?? "",
        responsable_id: area.responsable_id ?? "",
      })
    } else {
      setForm(EMPTY)
    }
    setErrors({})
    setServerError("")
  }, [area, open])

  function handleField(key: keyof FormData) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      const val = e.target.value
      setForm((prev) => ({ ...prev, [key]: val }))
      if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }))
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errs = validate(form)
    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      return
    }
    setSubmitting(true)
    setServerError("")
    try {
      if (isEdit && area) {
        await updateArea(area.id, {
          nombre: form.nombre.trim(),
          descripcion: form.descripcion.trim() || undefined,
          responsable_id: form.responsable_id || undefined,
        })
      } else {
        const payload: AreaCreate = {
          empresa_id: empresaId ?? getEmpresaActivaId() ?? "",
          nombre: form.nombre.trim(),
          descripcion: form.descripcion.trim() || undefined,
          responsable_id: form.responsable_id || undefined,
        }
        await createArea(payload)
      }
      onSuccess()
    } catch {
      setServerError("Ocurrió un error al guardar. Intentá de nuevo.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Editar área" : "Nueva área"}</DialogTitle>
        </DialogHeader>

        <form id="area-form" onSubmit={handleSubmit} noValidate>
          <div className="flex flex-col gap-4 py-2">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="nombre">
                Nombre
                <span className="ml-0.5 text-destructive" aria-hidden>*</span>
              </Label>
              <Input
                id="nombre"
                value={form.nombre}
                onChange={handleField("nombre")}
                aria-invalid={Boolean(errors.nombre)}
                aria-required
                maxLength={100}
              />
              {errors.nombre && (
                <p className="text-xs text-destructive" role="alert">{errors.nombre}</p>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="descripcion">Descripción</Label>
              <Textarea
                id="descripcion"
                value={form.descripcion}
                onChange={handleField("descripcion")}
                rows={3}
                className="resize-none"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="responsable_id">
                Responsable <span className="text-muted-foreground">(opcional)</span>
              </Label>
              <select
                id="responsable_id"
                value={form.responsable_id}
                onChange={handleField("responsable_id")}
                className={SELECT_CLASS}
              >
                <option value="">Sin responsable asignado</option>
                {empleados.map((emp) => (
                  <option key={emp.id} value={emp.id}>
                    {emp.nombre} {emp.apellido} — {emp.roles?.[0] ?? emp.cargo}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {serverError && (
            <p className="mt-2 text-sm text-destructive" role="alert">{serverError}</p>
          )}
        </form>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            className="min-h-11"
            onClick={onClose}
            disabled={submitting}
          >
            Cancelar
          </Button>
          <Button
            type="submit"
            form="area-form"
            className="min-h-11"
            disabled={submitting}
          >
            {submitting ? "Guardando..." : isEdit ? "Guardar cambios" : "Crear área"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
