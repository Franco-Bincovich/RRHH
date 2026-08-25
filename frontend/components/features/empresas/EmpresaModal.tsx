"use client"

import { useState, useEffect } from "react"

import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { FormErrores } from "@/components/ui/FormErrores"
import { createEmpresa, updateEmpresa } from "@/services/empresas"
import type { Empresa, EmpresaCreate } from "@/types/empresa"

import { EmpresaFormFields } from "./EmpresaFormFields"
import { EMPTY_EMPRESA, validarEmpresa, type EmpresaFormData, type EmpresaFormErrors } from "./empresaForm"
import { avisarGuardado } from "@/components/features/shared/avisoGuardado"

/**
 * Alta y edición de una empresa. ORQUESTADOR: el ciclo de vida del formulario (abrir, escribir,
 * validar, guardar, cerrar).
 *
 * ⚠️ ESTABA EN **226 LÍNEAS CONTRA UN LÍMITE DE 150** —deuda anotada en CLAUDE.md desde antes de
 * esta tanda— y el patrón de modal de formulario del bloque B lo llevaba a 241. Se partió en tres
 * por responsabilidad, con el molde que áreas ya tenía:
 *   · `empresaForm.ts`        — la definición del formulario y sus dos reglas de validación.
 *   · `EmpresaFormFields.tsx` — el render de los campos y el SEGUNDO nivel de la validación.
 *   · este archivo            — el ciclo de vida y el PRIMER nivel (el banner con la cuenta).
 */
interface EmpresaModalProps {
  open: boolean
  onClose: () => void
  onSuccess: (empresa: Empresa) => void
  empresa?: Empresa
}

export function EmpresaModal({ open, onClose, onSuccess, empresa }: EmpresaModalProps) {
  const isEdit = Boolean(empresa)
  const [form, setForm]             = useState<EmpresaFormData>(EMPTY_EMPRESA)
  const [errors, setErrors]         = useState<EmpresaFormErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState("")

  useEffect(() => {
    if (empresa) {
      setForm({
        nombre: empresa.nombre,
        razon_social: empresa.razon_social ?? "",
        cuit: empresa.cuit ?? "",
        direccion: empresa.direccion ?? "",
        telefono: empresa.telefono ?? "",
        email: empresa.email ?? "",
        logo_url: empresa.logo_url ?? "",
      })
    } else {
      setForm(EMPTY_EMPRESA)
    }
    setErrors({})
    setServerError("")
  }, [empresa, open])

  function handleField(key: keyof EmpresaFormData) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const val = e.target.value
      setForm((prev) => ({ ...prev, [key]: val }))
      if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }))
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errs = validarEmpresa(form)
    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      return
    }
    setSubmitting(true)
    setServerError("")
    try {
      let result: Empresa
      const payload: EmpresaCreate = {
        nombre: form.nombre.trim(),
        razon_social: form.razon_social.trim() || undefined,
        cuit: form.cuit.trim() || undefined,
        direccion: form.direccion.trim() || undefined,
        telefono: form.telefono.trim() || undefined,
        email: form.email.trim() || undefined,
        logo_url: form.logo_url.trim() || undefined,
      }
      if (isEdit && empresa) {
        result = await updateEmpresa(empresa.id, payload)
      } else {
        result = await createEmpresa(payload)
      }
      avisarGuardado("Empresa", "f", isEdit)
      onSuccess(result)
    } catch (err) {
      setServerError(
        err instanceof Error ? err.message : "Ocurrió un error al guardar. Intentá de nuevo.",
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      {/* El ancho (560px) y los campos de 34px los pone el patrón, no el modal: por eso ya no
          lleva `max-w-lg`. */}
      <DialogContent patron="formulario">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Editar empresa" : "Nueva empresa"}</DialogTitle>
          {/* 🔴 UNA LÍNEA QUE EXPLICA LA CONSECUENCIA, no lo que el modal es (§3). Lo que el
              usuario no puede deducir de los campos es que una empresa nueva aparece en el
              SELECTOR DEL SIDEBAR de todo el equipo y pasa a ser una opción en cada alta. */}
          <DialogDescription>
            {isEdit
              ? "Los cambios se ven en el selector de empresa del sidebar y en todo listado que muestre el nombre."
              : "La empresa aparece en el selector del sidebar de todo el equipo y pasa a ser elegible en cada alta."}
          </DialogDescription>
        </DialogHeader>

        <form id="empresa-form" onSubmit={handleSubmit} noValidate>
          <div className="flex flex-col gap-4 py-2">
            {/* El PRIMER nivel de la validación es la CUENTA, no la lista de campos: el "qué
                corrijo" lo contesta el segundo nivel, en cada campo. */}
            <FormErrores cantidad={Object.values(errors).filter(Boolean).length} />
            <EmpresaFormFields form={form} errors={errors} onField={handleField} />
          </div>

          {serverError && (
            <p className="mt-2 text-sm text-destructive" role="alert">{serverError}</p>
          )}
        </form>

        <DialogFooter>
          <Button type="button" variant="outline" className="min-h-11" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button type="submit" form="empresa-form" className="min-h-11" disabled={submitting}>
            {submitting ? "Guardando..." : isEdit ? "Guardar cambios" : "Crear empresa"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
