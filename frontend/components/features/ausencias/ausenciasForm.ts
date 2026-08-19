import type { AusenciaCreate, AusenciaUpdate } from "@/types/ausencias"

/** Shape del form de ausencia + constantes, validación y armado de payload (sin JSX). */
export type AusenciaFormData = {
  empresa_id: string
  empleado_id: string
  tipo_id: string
  fecha_desde: string
  fecha_hasta: string
  justificada: boolean
  motivo: string
}

export type AusenciaFormErrors = Partial<Record<keyof AusenciaFormData | "nuevo_tipo", string>>

export const EMPTY_AUSENCIA: AusenciaFormData = {
  empresa_id: "", empleado_id: "", tipo_id: "",
  fecha_desde: "", fecha_hasta: "", justificada: false, motivo: "",
}

export const NUEVO_TIPO = "__nuevo__"

// mandos_medios no elige empresa (la deriva el backend del empleado); no se exige empresa_id.
export function validateAusencia(form: AusenciaFormData, requireEmpresa: boolean): AusenciaFormErrors {
  const e: AusenciaFormErrors = {}
  if (requireEmpresa && !form.empresa_id) e.empresa_id = "Requerido"
  if (!form.empleado_id) e.empleado_id = "Requerido"
  if (!form.tipo_id || form.tipo_id === NUEVO_TIPO) e.tipo_id = "Seleccioná un tipo"
  if (!form.fecha_desde) e.fecha_desde = "Requerido"
  if (!form.fecha_hasta) e.fecha_hasta = "Requerido"
  if (form.fecha_desde && form.fecha_hasta && form.fecha_hasta < form.fecha_desde)
    e.fecha_hasta = "Debe ser igual o posterior al inicio"
  return e
}

/** Payload de alta (empleado_id incluido; motivo vacío → undefined). */
export function toAusenciaCreate(form: AusenciaFormData): AusenciaCreate {
  return {
    empleado_id: form.empleado_id,
    tipo_id: form.tipo_id,
    fecha_desde: form.fecha_desde,
    fecha_hasta: form.fecha_hasta,
    justificada: form.justificada,
    motivo: form.motivo.trim() || undefined,
  }
}

/** Payload de edición (sin empleado/empresa; motivo "" → backend lo normaliza a null). */
export function toAusenciaUpdate(form: AusenciaFormData): AusenciaUpdate {
  return {
    tipo_id: form.tipo_id,
    fecha_desde: form.fecha_desde,
    fecha_hasta: form.fecha_hasta,
    justificada: form.justificada,
    motivo: form.motivo.trim(),
  }
}
