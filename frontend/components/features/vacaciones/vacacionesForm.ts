import type {
  SolicitudVacacionesCreate, TipoVacacion, VacacionPendienteCreate,
} from "@/types/vacaciones"

/** Shape del form de alta de vacaciones + constantes y validación puras (sin JSX). */
export type VacacionFormData = {
  empresa_id: string
  empleado_id: string
  tipo: TipoVacacion
  fecha_desde: string
  fecha_hasta: string
  comentario: string
  /** Año al que corresponde la licencia. Se pide en los dos casos (tomada y pendiente). */
  periodo: string
  /** Tildado = no se tomó: sin fechas, con período y cantidad de días. Decide a qué tabla va. */
  pendiente: boolean
  /** Solo cuando pendiente=true: cuántos días quedaron sin tomar. */
  dias_pendientes: string
  /** Tilde "Liquidada". El backend guarda un entero (admite parcial); la UI lo trata binario. */
  liquidada: boolean
}

export type VacacionFormErrors = Partial<Record<keyof VacacionFormData, string>>

export const EMPTY_VACACION: VacacionFormData = {
  empresa_id: "", empleado_id: "", tipo: "vacaciones",
  fecha_desde: "", fecha_hasta: "", comentario: "",
  periodo: String(new Date().getFullYear()), pendiente: false,
  dias_pendientes: "", liquidada: false,
}

export const TIPOS_VACACION: { value: TipoVacacion; label: string }[] = [
  { value: "vacaciones",      label: "Vacaciones"       },
  { value: "semana_free",     label: "Semana free"      },
  { value: "dia_free",        label: "Día free"         },
  { value: "permiso_especial",label: "Permiso especial" },
]

/** Días inclusivos entre dos fechas ISO; 0 si el rango es inválido o incompleto. */
export function calcDias(desde: string, hasta: string): number {
  if (!desde || !hasta || hasta < desde) return 0
  return Math.round((new Date(hasta).getTime() - new Date(desde).getTime()) / 86400000) + 1
}

/** Días que la solicitud consume, sea tomada (por fechas) o pendiente (a mano). */
export function diasDelForm(form: VacacionFormData): number {
  return form.pendiente ? Number(form.dias_pendientes) || 0 : calcDias(form.fecha_desde, form.fecha_hasta)
}

function validarPeriodo(periodo: string): string | undefined {
  if (!periodo) return "El período es requerido"
  const n = Number(periodo)
  if (!Number.isInteger(n) || n < 2000 || n > 2100) return "Período inválido (2000–2100)"
  return undefined
}

// mandos_medios no elige empresa (la deriva el backend del empleado); no se exige empresa_id.
export function validateVacacion(form: VacacionFormData, requireEmpresa: boolean): VacacionFormErrors {
  const errors: VacacionFormErrors = {}
  if (requireEmpresa && !form.empresa_id) errors.empresa_id = "La empresa es requerida"
  if (!form.empleado_id) errors.empleado_id = "El colaborador es requerido"

  const errPeriodo = validarPeriodo(form.periodo)
  if (errPeriodo) errors.periodo = errPeriodo

  if (form.pendiente) {
    // Sin fechas a propósito: un día no tomado no tiene fecha porque nadie faltó ningún día.
    const n = Number(form.dias_pendientes)
    if (!form.dias_pendientes) errors.dias_pendientes = "La cantidad de días es requerida"
    else if (!Number.isInteger(n) || n <= 0) errors.dias_pendientes = "Tiene que ser un número entero mayor a 0"
    return errors
  }

  if (!form.fecha_desde) errors.fecha_desde = "La fecha de inicio es requerida"
  if (!form.fecha_hasta) errors.fecha_hasta = "La fecha de fin es requerida"
  if (form.fecha_desde && form.fecha_hasta && form.fecha_hasta < form.fecha_desde)
    errors.fecha_hasta = "La fecha de fin debe ser igual o posterior al inicio"
  return errors
}

/**
 * Payload de una licencia TOMADA (va a solicitudes_vacaciones). `liquidada` se traduce a
 * dias_liquidados = todos los días: el backend guarda un entero para admitir liquidación
 * PARCIAL, aunque hoy la UI solo ofrezca el todo-o-nada. Si RRHH confirma que puede ser
 * parcial, cambia este input y nada más — el modelo ya lo soporta (ver migración 083).
 */
export function payloadTomada(form: VacacionFormData): SolicitudVacacionesCreate {
  return {
    empleado_id: form.empleado_id,
    fecha_desde: form.fecha_desde,
    fecha_hasta: form.fecha_hasta,
    tipo: form.tipo,
    comentario: form.comentario.trim() || undefined,
    periodo: Number(form.periodo),
    dias_liquidados: form.liquidada ? calcDias(form.fecha_desde, form.fecha_hasta) : 0,
  }
}

/** Payload de días NO tomados (va a vacaciones_pendientes). Sin fechas ni tipo. */
export function payloadPendiente(form: VacacionFormData): VacacionPendienteCreate {
  const dias = Number(form.dias_pendientes)
  return {
    empleado_id: form.empleado_id,
    periodo: Number(form.periodo),
    dias,
    dias_liquidados: form.liquidada ? dias : 0,
    comentario: form.comentario.trim() || undefined,
  }
}
