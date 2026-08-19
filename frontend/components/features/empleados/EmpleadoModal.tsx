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
import { createEmpleado, updateEmpleado } from "@/services/empleados"
import type { Empleado } from "@/types/empleado"
import { EMPTY, type AutocompleteKey, type FormData, type FormErrors, type TextKey } from "./modal/_constants"
import { buildPayload, toFormData, validate } from "./modal/form-utils"
import { useEmpleadoFormData } from "./modal/useEmpleadoFormData"
import { DatosPersonalesFields } from "./modal/DatosPersonalesFields"
import { DatosLaboralesFields } from "./modal/DatosLaboralesFields"

interface EmpleadoModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
  empleado?: Empleado
}

export function EmpleadoModal({ open, onClose, onSuccess, empleado }: EmpleadoModalProps) {
  const isEdit = Boolean(empleado)
  const [form, setForm]             = useState<FormData>(EMPTY)
  const [errors, setErrors]         = useState<FormErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState("")

  const { empresas, empresasLoading, areas, areasLoading, rolesSugeridos, seleccionables } =
    useEmpleadoFormData(open, isEdit, form.empresa_id, isEdit ? empleado?.empresa_id ?? "" : form.empresa_id)

  // Resetear formulario al abrir/cerrar
  useEffect(() => {
    setForm(empleado ? toFormData(empleado) : EMPTY)
    setErrors({})
    setServerError("")
  }, [empleado, open])

  // Setter único: actualiza un campo y limpia su error. El orquestador es el dueño del estado.
  function setField<K extends keyof FormData>(key: K, value: FormData[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
    if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }))
  }
  const field = (key: TextKey) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setField(key, e.target.value)
  const onValue = (key: AutocompleteKey) => (value: string) => setField(key, value)
  const onLider = (value: boolean) => setField("es_lider", value)
  const handleRolesChange = (roles: string[]) => setField("roles", roles)

  function handleEmpresaChange(e: React.ChangeEvent<HTMLSelectElement>) {
    // Resetear área al cambiar empresa para evitar incoherencias
    setForm((prev) => ({ ...prev, empresa_id: e.target.value, area_id: "" }))
    setErrors((prev) => ({ ...prev, empresa_id: undefined, area_id: undefined }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errs = validate(form, isEdit)
    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      return
    }
    setSubmitting(true)
    setServerError("")
    const base = buildPayload(form)
    try {
      if (isEdit && empleado) {
        await updateEmpleado(empleado.id, base)
      } else {
        await createEmpleado({ ...base, empresa_id: form.empresa_id })
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
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Editar empleado" : "Nuevo empleado"}</DialogTitle>
        </DialogHeader>

        <form id="empleado-form" onSubmit={handleSubmit} noValidate className="space-y-5">
          <section>
            <h3 className="mb-3 text-sm font-semibold text-foreground">Información personal</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <DatosPersonalesFields form={form} errors={errors} field={field} onValue={onValue} />
            </div>
          </section>

          <section>
            <h3 className="mb-3 text-sm font-semibold text-foreground">Información laboral</h3>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <DatosLaboralesFields
                form={form}
                errors={errors}
                isEdit={isEdit}
                empresas={empresas}
                empresasLoading={empresasLoading}
                areas={areas}
                areasLoading={areasLoading}
                seleccionables={seleccionables} currentEmpleadoId={empleado?.id}
                rolesSugeridos={rolesSugeridos}
                field={field}
                onEmpresaChange={handleEmpresaChange}
                onRolesChange={handleRolesChange}
                onValue={onValue}
                onLider={onLider}
              />
            </div>
          </section>

          {serverError && (
            <p className="text-sm text-destructive" role="alert">{serverError}</p>
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
            form="empleado-form"
            className="min-h-11"
            disabled={submitting}
          >
            {submitting ? "Guardando..." : isEdit ? "Guardar cambios" : "Crear empleado"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
