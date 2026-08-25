"use client"

import { useState, useEffect } from "react"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { FormErrores } from "@/components/ui/FormErrores"
import { AreaFormFields } from "@/components/features/areas/AreaFormFields"
import { EMPTY, type FormData, type FormErrors } from "@/components/features/areas/areaForm"
import { guardarArea } from "@/components/features/areas/guardarArea"
import { fetchEmpresas } from "@/services/empresas"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Empresa } from "@/types/empresa"
import type { Area } from "@/types/area"
import { avisarGuardado } from "@/components/features/shared/avisoGuardado"

interface AreaModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
  area?: Area
  /** empresa_id explícito (tab de empresa). Si no se pasa, usa la empresa activa. */
  empresaId?: string
}

export function AreaModal({ open, onClose, onSuccess, area, empresaId }: AreaModalProps) {
  const isEdit = Boolean(area)
  const [form, setForm] = useState<FormData>(EMPTY)
  const [errors, setErrors] = useState<FormErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState("")
  const [empresas, setEmpresas] = useState<Empresa[]>([])

  useEffect(() => {
    // Solo en el alta: en la edición el select no se muestra (un área no se muda de sociedad).
    if (!open || area) return
    fetchEmpresas().then((r) => setEmpresas(r.items.filter((e) => e.activa))).catch(() => {})
  }, [open, area])

  useEffect(() => {
    if (area) {
      setForm({
        empresa_id: area.empresa_id ?? "",
        nombre: area.nombre,
        descripcion: area.descripcion ?? "",
        responsable_id: area.responsable_id ?? "",
      })
    } else {
      // Preseleccionada con la empresa del contexto (sidebar o tab). En consolidado queda "" y
      // la validación lo frena: antes salía a la red y volvía como 500.
      setForm({ ...EMPTY, empresa_id: empresaId ?? getEmpresaActivaId() ?? "" })
    }
    setErrors({})
    setServerError("")
  }, [area, open, empresaId])

  function handleField(key: keyof FormData) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      const val = e.target.value
      setForm((prev) => ({ ...prev, [key]: val }))
      if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }))
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setServerError("")
    try {
      const errs = await guardarArea(form, area)
      if (errs) {
        setErrors(errs)
        return
      }
      avisarGuardado("Área", "f", isEdit)
      onSuccess()
    } catch {
      setServerError("Ocurrió un error al guardar. Intentá de nuevo.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      {/* El ancho (560px) y los campos de 34px los pone el patrón, no el modal: por eso ya no
          lleva `max-w-md`. */}
      <DialogContent patron="formulario">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Editar área" : "Nueva área"}</DialogTitle>
          {/* 🔴 UNA LÍNEA QUE EXPLICA LA CONSECUENCIA, no lo que el modal es (§3). Lo que el
              usuario no puede deducir mirando los campos es que el área es POR EMPRESA y que de
              ella cuelgan el filtro de área de media docena de pantallas. */}
          <DialogDescription>
            {isEdit
              ? "Los cambios se ven al instante en la ficha de cada colaborador del área y en los filtros que la usan."
              : "El área queda disponible para asignar colaboradores y para filtrar por ella en el resto del sistema."}
          </DialogDescription>
        </DialogHeader>

        <form id="area-form" onSubmit={handleSubmit} noValidate>
          {/* El PRIMER nivel de la validación es la CUENTA, no la lista de campos: el "qué
              corrijo" lo contesta el segundo nivel, en cada campo. */}
          <FormErrores cantidad={Object.values(errors).filter(Boolean).length} />

          <AreaFormFields form={form} errors={errors} empresas={empresas}
                          responsableNombre={area?.responsable_nombre ?? undefined}
                          onResponsable={(id) => setForm((p) => ({ ...p, responsable_id: id }))}
                          isEdit={isEdit} onField={handleField} />

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
