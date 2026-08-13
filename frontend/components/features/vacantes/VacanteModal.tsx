"use client"

import { useState, useEffect } from "react"

import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { VacanteCamposBase } from "@/components/features/vacantes/VacanteCamposBase"
import { useVacanteCatalogos } from "@/components/features/vacantes/useVacanteCatalogos"
import { EMPTY_VACANTE, payloadVacante, validateVacante } from "@/components/features/vacantes/vacanteForm"
import type { VacanteFormData, VacanteFormErrors } from "@/components/features/vacantes/vacanteForm"
import { createVacante } from "@/services/vacantes"
import { getEmpresaActivaId } from "@/services/empresaStore"

/**
 * Alta de vacante. Orquestador: estado del form, carga de catálogos, handlers y submit.
 *
 * Estaba en 251/150 y el corte NO fue por campos —son cuatro y el DOM los alterna, ver
 * VacanteCamposBase— sino por CAPAS, en tres: lo puro en vacanteForm.ts, la vista en
 * VacanteCamposBase, los catálogos en useVacanteCatalogos, y acá la máquina de estado del form.
 * 📌 Es acá donde aterriza la feature: el handler que copia el perfil al form es orquestación,
 * y el selector en sí nace en su propio componente.
 *
 * 🚩 NO TIENE UN SOLO TEST, verificado por mutación: anular una validación entera deja la suite
 * en verde. Hoy solo lo cubre `tsc`. Por eso la validación y el payload salieron a un módulo
 * puro: ahí sí se testean sin montar el modal.
 */

interface VacanteModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

export function VacanteModal({ open, onClose, onSuccess }: VacanteModalProps) {
  const [form, setForm] = useState<VacanteFormData>(EMPTY_VACANTE)
  const [errors, setErrors] = useState<VacanteFormErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState("")
  const { empresas, areas, areasLoading } = useVacanteCatalogos(open, form.empresa_id)

  // Inicializar form al abrir, pre-seleccionar empresa activa del topbar
  useEffect(() => {
    if (!open) return
    const activa = getEmpresaActivaId() ?? ""
    setForm({ ...EMPTY_VACANTE, empresa_id: activa })
    setErrors({})
    setServerError("")
  }, [open])

  function field(key: keyof VacanteFormData) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
      const val = e.target.value
      setForm((prev) => ({ ...prev, [key]: val }))
      if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }))
    }
  }

  function handleEmpresaChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const val = e.target.value
    setForm((prev) => ({ ...prev, empresa_id: val, area_id: "" }))
    setErrors((prev) => ({ ...prev, empresa_id: undefined, area_id: undefined }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const errs = validateVacante(form)
    if (Object.keys(errs).length > 0) {
      setErrors(errs)
      return
    }
    setSubmitting(true)
    setServerError("")
    try {
      await createVacante(payloadVacante(form))
      onSuccess()
    } catch {
      setServerError("Ocurrió un error al guardar. Intentá de nuevo.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose() }}>
      <DialogContent className="max-h-[90vh] max-w-lg overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Nueva vacante</DialogTitle>
        </DialogHeader>

        <form id="vacante-form" onSubmit={handleSubmit} noValidate>
          <VacanteCamposBase
            form={form} errors={errors} empresas={empresas} areas={areas}
            areasLoading={areasLoading} onEmpresaChange={handleEmpresaChange} field={field}
          />

          {serverError && (
            <p className="mt-2 text-sm text-destructive" role="alert">{serverError}</p>
          )}
        </form>

        <DialogFooter>
          <Button type="button" variant="outline" className="min-h-11" onClick={onClose} disabled={submitting}>
            Cancelar
          </Button>
          <Button type="submit" form="vacante-form" className="min-h-11" disabled={submitting}>
            {submitting ? "Guardando..." : "Crear vacante"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
