"use client"

import { useEffect, useState } from "react"
import { toast } from "sonner"

import {
  EMPTY_AUSENCIA, toAusenciaCreate, toAusenciaUpdate, validateAusencia,
  type AusenciaFormData, type AusenciaFormErrors,
} from "@/components/features/ausencias/ausenciasForm"
import { crearAusenciaConAdjuntos, updateAusencia } from "@/services/ausencias"
import { getEmpresaActivaId } from "@/services/empresaStore"
import type { Ausencia } from "@/types/ausencias"

/**
 * Estado y handlers del formulario de ausencia. El componente queda con el markup.
 *
 * Extraído de `AusenciaModal.tsx`, que estaba en 149 contra un límite de 150 y no admitía una
 * línea más — y lo que viene (el select encadenado padre → hijo de la jerarquía de tipos) son
 * varias. La lógica se movió VERBATIM: mismo `useEffect` de reset, mismos handlers, mismo
 * manejo de errores y el mismo toast de adjuntos fallidos.
 *
 * ⚠️ El reset vive en un `useEffect` sobre `open` y NO en el montaje: el modal no se desmonta al
 * cerrarse, así que sin ese efecto la segunda apertura mostraría los datos de la primera.
 */
export function useAusenciaForm(open: boolean, editing: Ausencia | null | undefined, isMando: boolean) {
  const [form, setForm] = useState<AusenciaFormData>(EMPTY_AUSENCIA)
  const [errors, setErrors] = useState<AusenciaFormErrors>({})
  const [submitting, setSubmitting] = useState(false)
  const [serverError, setServerError] = useState("")
  const [pendientes, setPendientes] = useState<File[]>([])

  useEffect(() => {
    if (!open) return
    setErrors({})
    setServerError("")
    setPendientes([])
    if (editing) {
      setForm({
        empresa_id: editing.empresa_id, empleado_id: editing.empleado_id, tipo_id: editing.tipo_id,
        fecha_desde: editing.fecha_desde, fecha_hasta: editing.fecha_hasta,
        justificada: editing.justificada, motivo: editing.motivo ?? "",
      })
    } else {
      setForm({ ...EMPTY_AUSENCIA, empresa_id: isMando ? "" : (getEmpresaActivaId() ?? "") })
    }
  }, [open, editing, isMando])

  function field(key: keyof AusenciaFormData) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
      setForm((p) => ({ ...p, [key]: e.target.value }))
      if (errors[key]) setErrors((p) => ({ ...p, [key]: undefined }))
    }
  }

  async function submit(onSuccess: () => void) {
    const errs = validateAusencia(form, !isMando)
    if (Object.keys(errs).length > 0) { setErrors(errs); return }
    setSubmitting(true)
    setServerError("")
    try {
      if (editing) await updateAusencia(editing.id, toAusenciaUpdate(form))
      else { const { fallidos } = await crearAusenciaConAdjuntos(toAusenciaCreate(form), pendientes); if (fallidos > 0) toast.warning(`La ausencia se registró, pero ${fallidos} documento(s) no se pudo adjuntar. Reintentá desde "Documentos" en el listado.`) }
      onSuccess()
    } catch (err: unknown) {
      setServerError(err instanceof Error ? err.message : "Ocurrió un error al guardar")
    } finally {
      setSubmitting(false)
    }
  }

  return {
    form, setForm, errors, setErrors, submitting, serverError, pendientes, setPendientes,
    field, submit,
  }
}
